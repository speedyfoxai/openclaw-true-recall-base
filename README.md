# TrueRecall Base

**Purpose:** Real-time memory capture → Qdrant `memories_tr`

**Status:** ✅ Standalone capture system

---

## Overview

TrueRecall Base is the **foundation**. It watches OpenClaw sessions in real-time and stores every turn to Qdrant's `memories_tr` collection.

This is **required** for both addons: **Gems** and **Blocks**.

**Base does NOT include:**
- ❌ Curation (gem extraction)
- ❌ Topic clustering (blocks)
- ❌ Injection (context recall)

**For those features, install an addon after base.**

---

## Requirements

**Vector Database**

TrueRecall Base requires a vector database to store conversation embeddings. This can be:
- **Local** - Self-hosted Qdrant (recommended for privacy)
- **Cloud** - Managed Qdrant Cloud or similar service
- **Any IP-accessible** Qdrant instance

In this version, we use a **local Qdrant database** (`http://<QDRANT_IP>:6333`). The database must be reachable from the machine running the watcher daemon.

**Additional Requirements:**
- **Ollama** - For generating text embeddings (local or remote)
- **OpenClaw** - The session files to monitor
- **Linux systemd** - For running the watcher as a service

---

## Gotchas & Known Limitations

> ⚠️ **Embedding Dimensions:** `snowflake-arctic-embed2` outputs **1024 dimensions**, not 768. Ensure your Qdrant collection is configured with `"size": 1024`.

> ⚠️ **Hardcoded Sessions Path:** `SESSIONS_DIR` is hardcoded to `/root/.openclaw/agents/main/sessions`. To use a different path, modify `realtime_qdrant_watcher.py` to read from an environment variable:
> ```python
> SESSIONS_DIR = Path(os.getenv("OPENCLAW_SESSIONS_DIR", "/root/.openclaw/agents/main/sessions"))
> ```

---

## Three-Tier Architecture

```
true-recall-base (REQUIRED)
├── Core: Watcher daemon
└── Stores: memories_tr
    │
    ├──▶ true-recall-gems (ADDON)
    │   ├── Curator extracts gems → gems_tr
    │   └── Plugin injects gems into prompts
    │
    └──▶ true-recall-blocks (ADDON)
        ├── Topic clustering → topic_blocks_tr
        └── Contextual block retrieval

Note: Gems and Blocks are INDEPENDENT addons.
They both require Base, but don't work together.
Choose one: Gems OR Blocks (not both).
```

---

## Quick Start

### Option 1: Quick Install (Recommended)

```bash
cd /path/to/true-recall-base
./install.sh
```

#### What the Installer Does (Step-by-Step)

The `install.sh` script automates the entire setup process. Here's exactly what happens:

**Step 1: Interactive Configuration**
```
Configuration (press Enter for defaults):

Examples:
  Qdrant:  10.0.0.40:6333  (remote)  or  localhost:6333  (local)
  Ollama:  10.0.0.10:11434 (remote)  or  localhost:11434 (local)

Qdrant host:port [localhost:6333]: _
Ollama host:port [localhost:11434]: _
User ID [user]: _
```
- Prompts for Qdrant host:port (default: `localhost:6333`)
- Prompts for Ollama host:port (default: `localhost:11434`)
- Prompts for User ID (default: `user`)
- Press Enter to accept defaults, or type custom values

**Step 2: Configuration Confirmation**
```
Configuration:
  Qdrant: http://localhost:6333
  Ollama: http://localhost:11434
  User ID: user

Proceed? [Y/n]: _
```
- Shows the complete configuration
- Asks for confirmation (type `n` to cancel, Enter or `Y` to proceed)
- Exits cleanly if cancelled, no changes made

**Step 3: Systemd Service Generation**
- Creates a temporary service file at `/tmp/mem-qdrant-watcher.service`
- Inserts your configuration values (IPs, ports, user ID)
- Uses absolute path for the script location (handles spaces in paths)
- Sets up automatic restart on failure

**Step 4: Service Installation**
```bash
sudo cp /tmp/mem-qdrant-watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
```
- Copies the service file to systemd directory
- Reloads systemd to recognize the new service

**Step 5: Service Activation**
```bash
sudo systemctl enable --now mem-qdrant-watcher
```
- Enables the service to start on boot (`enable`)
- Starts the service immediately (`now`)

**Step 6: Verification**
```
==========================================
Installation Complete!
==========================================

Status:
● mem-qdrant-watcher.service - TrueRecall Base...
   Active: active (running)
```
- Displays the service status
- Shows it's active and running
- Provides commands to verify and monitor

**Post-Installation Commands:**
```bash
# Check service status anytime
sudo systemctl status mem-qdrant-watcher

# View live logs
sudo journalctl -u mem-qdrant-watcher -f

# Verify Qdrant collection
curl -s http://localhost:6333/collections/memories_tr | jq '.result.points_count'
```

#### Installer Requirements
- Must run as root or with sudo (for systemd operations)
- Must have execute permissions (`chmod +x install.sh`)
- Script must be run from the true-recall-base directory

### Option 2: Manual Install

```bash
cd /path/to/true-recall-base

# Copy service file
sudo cp watcher/mem-qdrant-watcher.service /etc/systemd/system/

# Edit the service file to set your IPs and user
sudo nano /etc/systemd/system/mem-qdrant-watcher.service

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable --now mem-qdrant-watcher
```

### Verify Installation

```bash
# Check service status
sudo systemctl status mem-qdrant-watcher

# Check collection
curl -s http://<QDRANT_IP>:6333/collections/memories_tr | jq '.result.points_count'
```

---

## Files

| File | Purpose |
|------|---------|
| `watcher/realtime_qdrant_watcher.py` | Capture daemon |
| `watcher/mem-qdrant-watcher.service` | Systemd service |
| `config.json` | Configuration template |

---

## Configuration

Edit `config.json` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://<QDRANT_IP>:6333` | Qdrant endpoint |
| `OLLAMA_URL` | `http://<OLLAMA_IP>:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | `snowflake-arctic-embed2` | Embedding model |
| `USER_ID` | `<USER_ID>` | User identifier |

---

## How It Works

### Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OpenClaw Chat  │────▶│  Session JSONL   │────▶│  Base Watcher   │
│   (You talking) │     │  (/sessions/*.jsonl)  │     │  (This daemon)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                        │
                                                        ▼
┌────────────────────────────────────────────────────────────────────┐
│                         PROCESSING PIPELINE                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Watch File   │─▶│ Parse Turn   │─▶│ Clean Text   │─▶│ Embed     │ │
│  │ (inotify)    │  │ (JSON→dict)  │  │ (strip md)   │  │ (Ollama)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────┬─────┘ │
│                                                              │       │
│  ┌───────────────────────────────────────────────────────────┘       │
│  │                                                                   │
│  ▼                                                                   │
│  ┌──────────────┐  ┌──────────────┐                                  │
│  │ Store to     │─▶│ Qdrant       │                                  │
│  │ memories_tr  │  │ (vector DB)  │                                  │
│  └──────────────┘  └──────────────┘                                  │
└────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Process

#### Step 1: File Watching

The watcher monitors OpenClaw session files in real-time:

```python
# From realtime_qdrant_watcher.py
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")
```

> ⚠️ **Known Limitation:** `SESSIONS_DIR` is currently hardcoded. To use a different path, patch the watcher script to read from an environment variable (e.g., `os.getenv("OPENCLAW_SESSIONS_DIR", "/root/.openclaw/agents/main/sessions")`).

**What happens:**
- Uses `inotify` or polling to watch the sessions directory
- Automatically detects the most recently modified `.jsonl` file
- Handles session rotation (when OpenClaw starts a new session)
- Maintains position in file to avoid re-processing old lines

#### Step 2: Turn Parsing

Each conversation turn is extracted from the JSONL file:

```json
// Example session file entry
{
  "type": "message",
  "message": {
    "role": "user",
    "content": "Hello, can you help me?",
    "timestamp": "2026-02-27T09:30:00Z"
  }
}
```

**What happens:**
- Reads new lines appended to the session file
- Parses JSON to extract role (user/assistant/system)
- Extracts content text
- Captures timestamp
- Generates unique turn ID from content hash + timestamp

**Code flow:**
```python
def parse_turn(line: str) -> Optional[Dict]:
    data = json.loads(line)
    if data.get("type") != "message":
        return None  # Skip non-message entries
    
    return {
        "id": hashlib.md5(f"{content}{timestamp}".encode()).hexdigest()[:16],
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "user_id": os.getenv("USER_ID", "default")
    }
```

#### Step 3: Content Cleaning

Before storage, content is normalized:

**Strips:**
- Markdown tables (`| column | column |`)
- Bold/italic markers (`**text**`, `*text*`)
- Inline code (`` `code` ``)
- Code blocks (```code```)
- Multiple consecutive spaces
- Leading/trailing whitespace

**Example:**
```
Input:  "Check this **important** table: | col1 | col2 |"
Output: "Check this important table"
```

**Why:** Clean text improves embedding quality and searchability.

#### Step 4: Embedding Generation

The cleaned content is converted to a vector embedding:

```python
def get_embedding(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text}
    )
    return response.json()["embedding"]
```

**What happens:**
- Sends text to Ollama API (10.0.0.10:11434)
- Uses `snowflake-arctic-embed2` model
- Returns **1024-dimensional vector** (not 768)
- Falls back gracefully if Ollama is unavailable

#### Step 5: Qdrant Storage

The complete turn data is stored to Qdrant:

```python
payload = {
    "user_id": user_id,
    "role": turn["role"],
    "content": cleaned_content[:2000],  # Size limit
    "timestamp": turn["timestamp"],
    "session_id": session_id,
    "source": "true-recall-base"
}

requests.put(
    f"{QDRANT_URL}/collections/memories_tr/points",
    json={"points": [{"id": turn_id, "vector": embedding, "payload": payload}]}
)
```

**Storage format:**
| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | User identifier |
| `role` | string | user/assistant/system |
| `content` | string | Cleaned text (max 2000 chars) |
| `timestamp` | string | ISO 8601 timestamp |
| `session_id` | string | Source session file |
| `source` | string | "true-recall-base" |

### Real-Time Performance

| Metric | Target | Actual |
|--------|--------|--------|
| Latency | < 500ms | ~100-200ms |
| Throughput | > 10 turns/sec | > 50 turns/sec |
| Embedding time | < 300ms | ~50-100ms |
| Qdrant write | < 100ms | ~10-50ms |

### Session Rotation Handling

When OpenClaw starts a new session:

1. New `.jsonl` file created in sessions directory
2. Watcher detects file change via `inotify`
3. Identifies most recently modified file
4. Switches to watching new file
5. Continues from position 0 of new file
6. Old file remains in `memories_tr` (already captured)

### Error Handling

**Qdrant unavailable:**
- Retries with exponential backoff
- Logs error, continues watching
- Next turn attempts storage again

**Ollama unavailable:**
- Cannot generate embeddings
- Logs error, skips turn
- Continues watching (no data loss in file)

**File access errors:**
- Handles permission issues gracefully
- Retries on temporary failures

### Collection Schema

**Qdrant collection: `memories_tr`**

```python
{
  "name": "memories_tr",
  "vectors": {
    "size": 1024,           # snowflake-arctic-embed2 dimension (1024, not 768)
    "distance": "Cosine"   # Similarity metric
  },
  "payload_schema": {
    "user_id": "keyword",  # Filterable
    "role": "keyword",     # Filterable
    "timestamp": "datetime",  # Range filterable
    "content": "text"      # Full-text searchable
  }
}
```

### Security Notes

- **No credential storage** in code
- All sensitive values via environment variables
- `USER_ID` isolates memories per user
- Cleaned content removes PII markers (but review your data)
- HTTPS recommended for production Qdrant/Ollama

---

## Using Memories with OpenClaw

### The "q" Command

**"q"** refers to your Qdrant memory system (`memories_tr` collection).

When interacting with OpenClaw agents, you can search your stored memories using:
- `search q <topic>` - Semantic search for past conversations
- `q <topic>` - Shortcut for the same

### Context Injection Instructions

**For OpenClaw System Prompt:**

Add these lines to your agent's system context to enable memory-aware responses:

```
## Memory System (q)

**"q" = Qdrant collection `memories_tr`** — your conversation history database.

### Memory Retrieval Rules

**Before saying "I don't know" or "I can't do that":**
1. **ALWAYS search q first** using the topic/keywords from the user's request
2. Incorporate findings INTO your response (not as footnotes)
3. Reference specific dates/details: "Based on our Feb 27th discussion..."

**Example workflow:**
```
User asks about X → Search q for X → Use retrieved memories → Answer
```

**WRONG:**
> "I searched Qdrant and found X. [Generic answer unrelated to X]"

**RIGHT:**
> "You asked me to fix this on Feb 27th — do you want me to apply the fix now?"

### When to Search q

**ALWAYS search automatically when:**
- Question references past events, conversations, or details
- User asks "remember when...", "what did we discuss...", "what did I tell you..."
- You're unsure if you have relevant context
- ANY question about configuration, memories, or past interactions

**DO NOT search for:**
- General knowledge questions you can answer directly
- Current time, weather, or factual queries
- Simple requests like "check my email" or "run a command"
- When you already have sufficient context in the conversation
```

### Search Priority

| Order | Source | When to Use |
|-------|--------|-------------|
| 1 | **q (Qdrant)** | First - semantic search of all conversations |
| 2 | `memory/` files | Fallback if q yields no results |
| 3 | Web search | Last resort |
| 4 | "I don't know" | Only after all above |

---

## Next Step

### ✅ Base is Complete

**You don't need to upgrade.** TrueRecall Base is a **fully functional, standalone memory system**. If you're happy with real-time capture and manual search via the `q` command, you can stop here.

Base gives you:
- ✅ Complete conversation history in Qdrant
- ✅ Semantic search via `search q <topic>`
- ✅ Full-text search capabilities
- ✅ Permanent storage of all conversations

**Upgrade only if** you want automatic context injection into prompts.

---

### Optional Addons

Install an **addon** for automatic curation and injection:

| Addon | Purpose | Status |
|-------|---------|--------|
| **Gems** | Extracts atomic gems from memories, injects into context | 🚧 Coming Soon |
| **Blocks** | Topic clustering, contextual block retrieval | 🚧 Coming Soon |

### Upgrade Paths

Once Base is running, you have two upgrade options:

#### Option 1: Gems (Atomic Memory)
**Best for:** Conversational context, quick recall

- **Curator** extracts "gems" (key insights) from `memories_tr`
- Stores curated gems in `gems_tr` collection
- **Injection plugin** recalls relevant gems into prompts automatically
- Optimized for: Chat assistants, help bots, personal memory

**Workflow:**
```
memories_tr → Curator → gems_tr → Injection → Context
```

#### Option 2: Blocks (Topic Clustering)
**Best for:** Document organization, topic-based retrieval

- Clusters conversations by topic automatically
- Creates `topic_blocks_tr` collection
- Retrieves entire contextual blocks on query
- Optimized for: Knowledge bases, document systems

**Workflow:**
```
memories_tr → Topic Engine → topic_blocks_tr → Retrieval → Context
```

**Note:** Gems and Blocks are **independent** addons. They both require Base, but you choose one based on your use case.

---

## Updating / Patching

If you already have TrueRecall Base installed and need to apply a bug fix or update:

### Quick Update (v1.2 Patch)

**Applies to:** Session file detection fix (picks wrong file when multiple sessions active)

```bash
# 1. Backup current watcher
cp /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py \
   /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py.bak.$(date +%Y%m%d)

# 2. Download latest watcher (choose one source)

# Option A: From GitHub
curl -o /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py \
  https://raw.githubusercontent.com/speedyfoxai/openclaw-true-recall-base/master/watcher/realtime_qdrant_watcher.py

# Option B: From GitLab
curl -o /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py \
  https://gitlab.com/mdkrush/true-recall-base/-/raw/master/watcher/realtime_qdrant_watcher.py

# Option C: From local git (if cloned)
cp /path/to/true-recall-base/watcher/realtime_qdrant_watcher.py \
  /root/.openclaw/workspace/skills/qdrant-memory/scripts/

# 3. Stop old watcher
pkill -f realtime_qdrant_watcher

# 4. Start new watcher
python3 /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py --daemon

# 5. Verify
ps aux | grep watcher
lsof -p $(pgrep -f realtime_qdrant_watcher) | grep jsonl
```

### Update with Git (If Cloned)

```bash
cd /path/to/true-recall-base
git pull origin master

# Copy updated files
cp watcher/realtime_qdrant_watcher.py \
   /root/.openclaw/workspace/skills/qdrant-memory/scripts/

# Copy optional: backfill script
cp scripts/backfill_memory_to_q.py \
   /root/.openclaw/workspace/skills/qdrant-memory/scripts/ 2>/dev/null || true

# Restart watcher
sudo systemctl restart mem-qdrant-watcher
# OR manually:
pkill -f realtime_qdrant_watcher
python3 /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py --daemon
```

### Verify Update Applied

```bash
# Check version in file
grep "v1.2" /root/.openclaw/workspace/skills/qdrant-memory/scripts/realtime_qdrant_watcher.py

# Verify watcher is running
ps aux | grep realtime_qdrant_watcher

# Confirm watching main session (not subagent)
lsof -p $(pgrep -f realtime_qdrant_watcher) | grep jsonl

# Check recent captures in Qdrant
curl -s "http://10.0.0.40:6333/collections/memories_tr/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "with_payload": true}' | jq -r '.result.points[].payload.timestamp'
```

### What's New in v1.2

| Feature | Benefit |
|---------|---------|
| **Priority-based session detection** | Always picks `agent:main:main` first |
| **Lock file validation** | Ignores stale/crashed session locks via PID check |
| **Inactive subagent filtering** | Skips sessions with `sessionFile=null` |
| **Backfill script** | Import historical memories from markdown files |

**No config changes required** - existing `config.json` works unchanged.

---

**Prerequisite for:** TrueRecall Gems, TrueRecall Blocks
