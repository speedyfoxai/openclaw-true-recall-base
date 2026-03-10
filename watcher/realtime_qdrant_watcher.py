#!/usr/bin/env python3
"""
TrueRecall v1.2 - Real-time Qdrant Watcher
Monitors OpenClaw sessions and stores to memories_tr instantly.

This is the CAPTURE component. For curation and injection, install v2.

Changelog:
- v1.2: Fixed session rotation bug - added inactivity detection (30s threshold)
        and improved file scoring to properly detect new sessions on /new or /reset
- v1.1: Added 1-second mtime polling for session rotation
- v1.0: Initial release
"""

import os
import sys
import json
import time
import signal
import hashlib
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "http://10.0.0.40:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "memories_tr")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "snowflake-arctic-embed2")
USER_ID = os.getenv("USER_ID", "rob")

# Paths
SESSIONS_DIR = Path(os.getenv("OPENCLAW_SESSIONS_DIR", "/root/.openclaw/agents/main/sessions"))

# State
running = True
last_position = 0
current_file = None
turn_counter = 0


def signal_handler(signum, frame):
    global running
    print(f"\nReceived signal {signum}, shutting down...", file=sys.stderr)
    running = False


def get_embedding(text: str) -> List[float]:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}", file=sys.stderr)
        return None


def clean_content(text: str) -> str:
    import re
    
    # Remove metadata JSON blocks
    text = re.sub(r'Conversation info \(untrusted metadata\):\s*```json\s*\{[\s\S]*?\}\s*```', '', text)
    
    # Remove thinking tags
    text = re.sub(r'\[thinking:[^\]]*\]', '', text)
    
    # Remove timestamp lines
    text = re.sub(r'\[\w{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} [A-Z]{3}\]', '', text)
    
    # Remove markdown tables
    text = re.sub(r'\|[^\n]*\|', '', text)
    text = re.sub(r'\|[-:]+\|', '', text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # Remove horizontal rules
    text = re.sub(r'---+', '', text)
    text = re.sub(r'\*\*\*+', '', text)
    
    # Remove excess whitespace
    text = re.sub(r'\n{3,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def chunk_text(text: str, max_chars: int = 6000, overlap: int = 200) -> list:
    """Split text into overlapping chunks for embedding.
    
    Args:
        text: Text to chunk
        max_chars: Max chars per chunk (6000 = safe for 4K token limit)
        overlap: Chars to overlap between chunks
    
    Returns:
        List of chunk dicts with 'text' and 'chunk_index'
    """
    if len(text) <= max_chars:
        return [{'text': text, 'chunk_index': 0, 'total_chunks': 1}]
    
    chunks = []
    start = 0
    chunk_num = 0
    
    while start < len(text):
        end = start + max_chars
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for paragraph break first
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + 500:
                end = para_break
            else:
                # Look for sentence break
                for delim in ['. ', '? ', '! ', '\n']:
                    sent_break = text.rfind(delim, start, end)
                    if sent_break > start + 500:
                        end = sent_break + 1
                        break
        
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 100:  # Skip tiny chunks
            chunks.append(chunk_text)
            chunk_num += 1
        
        start = end - overlap if end < len(text) else len(text)
    
    # Add metadata to each chunk
    total = len(chunks)
    return [{'text': c, 'chunk_index': i, 'total_chunks': total} for i, c in enumerate(chunks)]


def store_to_qdrant(turn: Dict[str, Any], dry_run: bool = False) -> bool:
    """Store a conversation turn to Qdrant, chunking if needed.
    
    For long content, splits into multiple chunks (no data loss).
    Each chunk gets its own point with chunk_index metadata.
    """
    if dry_run:
        print(f"[DRY RUN] Would store turn {turn['turn']} ({turn['role']}): {turn['content'][:60]}...")
        return True
    
    content = turn['content']
    chunks = chunk_text(content)
    
    if len(chunks) > 1:
        print(f"  📦 Chunking turn {turn['turn']}: {len(content)} chars → {len(chunks)} chunks", file=sys.stderr)
    
    turn_id = turn.get('turn', 0)
    base_time = datetime.now().strftime('%H%M%S')
    all_success = True
    
    for chunk_info in chunks:
        chunk_text_content = chunk_info['text']
        chunk_index = chunk_info['chunk_index']
        total_chunks = chunk_info['total_chunks']
        
        # Get embedding for this chunk
        vector = get_embedding(chunk_text_content)
        if vector is None:
            print(f"Failed to get embedding for turn {turn['turn']} chunk {chunk_index}", file=sys.stderr)
            all_success = False
            continue
        
        # Payload includes full content reference, chunk metadata
        payload = {
            "user_id": turn.get('user_id', USER_ID),
            "role": turn['role'],
            "content": chunk_text_content,  # Store chunk content (searchable)
            "full_content_length": len(content),  # Original length
            "turn": turn['turn'],
            "timestamp": turn.get('timestamp', datetime.now(timezone.utc).isoformat()),
            "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            "source": "true-recall-base",
            "curated": False,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks
        }
        
        # Generate unique ID for each chunk
        hash_bytes = hashlib.sha256(
            f"{USER_ID}:turn:{turn_id}:chunk{chunk_index}:{base_time}".encode()
        ).digest()[:8]
        point_id = int.from_bytes(hash_bytes, byteorder='big') % (2**63)
        
        try:
            response = requests.put(
                f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
                json={
                    "points": [{
                        "id": abs(point_id),
                        "vector": vector,
                        "payload": payload
                    }]
                },
                timeout=30
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error writing chunk {chunk_index} to Qdrant: {e}", file=sys.stderr)
            all_success = False
    
    return all_success


def is_lock_valid(lock_path: Path, max_age_seconds: int = 1800) -> bool:
    """Check if lock file is valid (not stale, PID exists)."""
    try:
        with open(lock_path, 'r') as f:
            data = json.load(f)
        
        # Check lock file age
        created = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        if (datetime.now(timezone.utc) - created).total_seconds() > max_age_seconds:
            return False
        
        # Check PID exists
        pid = data.get('pid')
        if pid and not os.path.exists(f"/proc/{pid}"):
            return False
        
        return True
    except Exception:
        return False


def get_current_session_file():
    """Find the most recently active session file.
    
    Priority (per subagent analysis consensus):
    1. Explicit agent:main:main lookup from sessions.json (highest priority)
    2. Lock files with valid PID + recent timestamp
    3. Parse sessions.json for other active sessions
    4. File scoring by mtime + size (fallback)
    """
    if not SESSIONS_DIR.exists():
        return None
    
    sessions_json = SESSIONS_DIR / "sessions.json"
    
    # PRIORITY 1: Explicit main session lookup
    if sessions_json.exists():
        try:
            with open(sessions_json, 'r') as f:
                sessions_data = json.load(f)
            
            # Look up agent:main:main explicitly
            main_session = sessions_data.get("agent:main:main", {})
            main_session_id = main_session.get('sessionId')
            
            if main_session_id:
                main_file = SESSIONS_DIR / f"{main_session_id}.jsonl"
                if main_file.exists():
                    return main_file
        except Exception as e:
            print(f"Warning: Failed to parse sessions.json for main session: {e}", file=sys.stderr)
    
    # PRIORITY 2: Lock files with PID validation
    lock_files = list(SESSIONS_DIR.glob("*.jsonl.lock"))
    valid_locks = [lf for lf in lock_files if is_lock_valid(lf)]
    
    if valid_locks:
        # Get the most recent valid lock file
        newest_lock = max(valid_locks, key=lambda p: p.stat().st_mtime)
        session_file = SESSIONS_DIR / newest_lock.name.replace('.jsonl.lock', '.jsonl')
        if session_file.exists():
            return session_file
    
    # PRIORITY 3: Parse sessions.json for other sessions with sessionFile
    if sessions_json.exists():
        try:
            with open(sessions_json, 'r') as f:
                sessions_data = json.load(f)
            
            active_session = None
            active_mtime = 0
            
            for session_key, session_info in sessions_data.items():
                # Skip if no sessionFile (inactive subagents have null)
                session_file_path = session_info.get('sessionFile')
                if not session_file_path:
                    continue
                
                session_file = Path(session_file_path)
                if session_file.exists():
                    mtime = session_file.stat().st_mtime
                    if mtime > active_mtime:
                        active_mtime = mtime
                        active_session = session_file
            
            if active_session:
                return active_session
        except Exception as e:
            print(f"Warning: Failed to parse sessions.json: {e}", file=sys.stderr)
    
    # PRIORITY 4: Score files by recency (mtime) + size
    files = list(SESSIONS_DIR.glob("*.jsonl"))
    if not files:
        return None
    
    def file_score(p: Path) -> float:
        try:
            stat = p.stat()
            mtime = stat.st_mtime
            size = stat.st_size
            return mtime + (size / 1e9)
        except Exception:
            return 0
    
    return max(files, key=file_score)


def parse_turn(line: str, session_name: str) -> Optional[Dict[str, Any]]:
    global turn_counter
    
    try:
        entry = json.loads(line.strip())
    except json.JSONDecodeError:
        return None
    
    if entry.get('type') != 'message' or 'message' not in entry:
        return None
    
    msg = entry['message']
    role = msg.get('role')
    
    if role in ('toolResult', 'system', 'developer'):
        return None
    
    if role not in ('user', 'assistant'):
        return None
    
    content = ""
    if isinstance(msg.get('content'), list):
        for item in msg['content']:
            if isinstance(item, dict) and 'text' in item:
                content += item['text']
    elif isinstance(msg.get('content'), str):
        content = msg['content']
    
    if not content:
        return None
    
    content = clean_content(content)
    if not content or len(content) < 5:
        return None
    
    turn_counter += 1
    
    return {
        'turn': turn_counter,
        'role': role,
        'content': content[:2000],
        'timestamp': entry.get('timestamp', datetime.now(timezone.utc).isoformat()),
        'user_id': USER_ID
    }


def process_new_lines(f, session_name: str, dry_run: bool = False):
    global last_position
    
    f.seek(last_position)
    
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        turn = parse_turn(line, session_name)
        if turn:
            if store_to_qdrant(turn, dry_run):
                print(f"✅ Turn {turn['turn']} ({turn['role']}) → Qdrant")
    
    last_position = f.tell()


def watch_session(session_file: Path, dry_run: bool = False):
    global last_position, turn_counter
    
    session_name = session_file.name.replace('.jsonl', '')
    print(f"Watching session: {session_file.name}")
    
    try:
        with open(session_file, 'r') as f:
            for line in f:
                turn_counter += 1
        last_position = session_file.stat().st_size
        print(f"Session has {turn_counter} existing turns, starting from position {last_position}")
    except Exception as e:
        print(f"Warning: Could not read existing turns: {e}", file=sys.stderr)
        last_position = 0
    
    last_session_check = time.time()
    last_data_time = time.time()  # Track when we last saw new data
    last_file_size = session_file.stat().st_size if session_file.exists() else 0
    
    INACTIVITY_THRESHOLD = 30  # seconds - if no data for 30s, check for new session
    
    # Check file exists before opening (handles deleted sessions)
    if not session_file.exists():
        print(f"Session file gone: {session_file.name}, looking for new session...", file=sys.stderr)
        return None
    
    # Track file handle for re-opening
    try:
        f = open(session_file, 'r')
        f.seek(last_position)
    except FileNotFoundError:
        print(f"Session file removed during open: {session_file.name}", file=sys.stderr)
        return None
    
    try:
        while running:
            if not session_file.exists():
                print("Session file removed, looking for new session...")
                f.close()
                return None
            
            current_time = time.time()
            
            # Check for newer session every 1 second
            if current_time - last_session_check > 1.0:
                last_session_check = current_time
                newest_session = get_current_session_file()
                if newest_session and newest_session != session_file:
                    print(f"Newer session detected: {newest_session.name}")
                    f.close()
                    return newest_session
            
            # Check if current file is stale (no new data for threshold)
            if current_time - last_data_time > INACTIVITY_THRESHOLD:
                try:
                    current_size = session_file.stat().st_size
                    # If file hasn't grown, check if another session is active
                    if current_size == last_file_size:
                        newest_session = get_current_session_file()
                        if newest_session and newest_session != session_file:
                            print(f"Current session inactive, switching to: {newest_session.name}")
                            f.close()
                            return newest_session
                    else:
                        # File grew, update tracking
                        last_file_size = current_size
                        last_data_time = current_time
                except Exception:
                    pass
            
            # Check if file has grown since last read
            try:
                current_size = session_file.stat().st_size
            except Exception:
                current_size = 0
            
            # Only process if file has grown
            if current_size > last_position:
                old_position = last_position
                process_new_lines(f, session_name, dry_run)
                
                # If we processed new data, update activity timestamp
                if last_position > old_position:
                    last_data_time = current_time
                    last_file_size = current_size
            else:
                # Re-open file handle to detect new writes
                f.close()
                time.sleep(0.05)  # Brief pause before re-opening
                f = open(session_file, 'r')
                f.seek(last_position)
            
            time.sleep(0.1)
    finally:
        f.close()
    
    return session_file


def watch_loop(dry_run: bool = False):
    global current_file, turn_counter
    
    while running:
        session_file = get_current_session_file()
        
        if session_file is None:
            print("No active session found, waiting...")
            time.sleep(1)
            continue
        
        if current_file != session_file:
            print(f"\nNew session detected: {session_file.name}")
            current_file = session_file
            turn_counter = 0
            last_position = 0
        
        result = watch_session(session_file, dry_run)
        
        if result is None:
            current_file = None
            time.sleep(0.5)


def main():
    global USER_ID
    
    parser = argparse.ArgumentParser(description="TrueRecall v1.1 - Real-time Memory Capture")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon")
    parser.add_argument("--once", "-o", action="store_true", help="Process once then exit")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write to Qdrant")
    parser.add_argument("--user-id", "-u", default=USER_ID, help=f"User ID (default: {USER_ID})")
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.user_id:
        USER_ID = args.user_id
    
    print(f"🔍 TrueRecall v1.1 - Real-time Memory Capture")
    print(f"📍 Qdrant: {QDRANT_URL}/{QDRANT_COLLECTION}")
    print(f"🧠 Ollama: {OLLAMA_URL}/{EMBEDDING_MODEL}")
    print(f"👤 User: {USER_ID}")
    print()
    
    if args.once:
        print("Running once...")
        session_file = get_current_session_file()
        if session_file:
            watch_session(session_file, args.dry_run)
        else:
            print("No session found")
    else:
        print("Running as daemon (Ctrl+C to stop)...")
        watch_loop(args.dry_run)


if __name__ == "__main__":
    main()
