#!/usr/bin/env python3
"""
Backfill memories_tr collection from memory markdown files.

Processes all .md files in /root/.openclaw/workspace/memory/
and stores them to Qdrant memories_tr collection.

Usage:
    python3 backfill_memory_to_q.py [--dry-run]
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import requests

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "http://10.0.0.40:6333")
COLLECTION_NAME = "memories_tr"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.0.0.10:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "snowflake-arctic-embed2")
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")
USER_ID = "rob"

def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text[:4000]},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Error getting embedding: {e}", file=sys.stderr)
        return None

def clean_content(text: str) -> str:
    """Clean markdown content for storage"""
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove excess whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def parse_memory_file(file_path: Path) -> List[Dict[str, Any]]:
    """Parse a memory markdown file into entries"""
    entries = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return entries
    
    # Extract date from filename
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.name)
    date_str = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
    
    # Split by session headers (## Session: or ## Update:)
    sessions = re.split(r'\n## ', content)
    
    for i, session in enumerate(sessions):
        if not session.strip():
            continue
        
        # Extract session title if present
        title_match = re.match(r'Session:\s*(.+)', session, re.MULTILINE)
        if not title_match:
            title_match = re.match(r'Update:\s*(.+)', session, re.MULTILINE)
        session_title = title_match.group(1).strip() if title_match else f"Session {i}"
        
        # Extract key events, decisions, and content
        # Look for bullet points and content
        sections = session.split('\n### ')
        
        for section in sections:
            if not section.strip():
                continue
            
            # Clean the content
            cleaned = clean_content(section)
            if len(cleaned) < 20:  # Skip very short sections
                continue
            
            entry = {
                'content': cleaned[:2000],
                'role': 'assistant',  # These are summaries
                'date': date_str,
                'session_title': session_title,
                'file': file_path.name,
                'source': 'memory-backfill'
            }
            entries.append(entry)
    
    return entries

def store_to_qdrant(entry: Dict[str, Any], dry_run: bool = False) -> bool:
    """Store a memory entry to Qdrant"""
    content = entry['content']
    
    if dry_run:
        print(f"[DRY RUN] Would store: {content[:60]}...")
        return True
    
    vector = get_embedding(content)
    if vector is None:
        return False
    
    # Generate deterministic ID
    hash_content = f"{USER_ID}:{entry['date']}:{content[:100]}"
    hash_bytes = hashlib.sha256(hash_content.encode()).digest()[:8]
    point_id = abs(int.from_bytes(hash_bytes, byteorder='big') % (2**63))
    
    payload = {
        'user_id': USER_ID,
        'role': entry.get('role', 'assistant'),
        'content': content,
        'date': entry['date'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source': entry.get('source', 'memory-backfill'),
        'file': entry.get('file', ''),
        'session_title': entry.get('session_title', ''),
        'curated': True  # Mark as curated since these are processed
    }
    
    try:
        response = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            json={'points': [{'id': point_id, 'vector': vector, 'payload': payload}]},
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error storing to Qdrant: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Backfill memory files to Qdrant')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run - do not write to Qdrant')
    parser.add_argument('--limit', '-l', type=int, default=None, help='Limit number of files to process')
    args = parser.parse_args()
    
    if not MEMORY_DIR.exists():
        print(f"Memory directory not found: {MEMORY_DIR}", file=sys.stderr)
        sys.exit(1)
    
    # Get all markdown files
    md_files = sorted(MEMORY_DIR.glob('*.md'))
    
    if args.limit:
        md_files = md_files[:args.limit]
    
    print(f"Found {len(md_files)} memory files to process")
    print(f"Target collection: {COLLECTION_NAME}")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Ollama URL: {OLLAMA_URL}")
    print()
    
    total_entries = 0
    stored = 0
    failed = 0
    
    for file_path in md_files:
        print(f"Processing: {file_path.name}")
        entries = parse_memory_file(file_path)
        
        for entry in entries:
            total_entries += 1
            if store_to_qdrant(entry, args.dry_run):
                stored += 1
                print(f"  ✅ Stored entry {stored}")
            else:
                failed += 1
                print(f"  ❌ Failed entry {failed}")
    
    print()
    print(f"Done! Processed {len(md_files)} files")
    print(f"Total entries: {total_entries}")
    print(f"Stored: {stored}")
    print(f"Failed: {failed}")

if __name__ == '__main__':
    main()
