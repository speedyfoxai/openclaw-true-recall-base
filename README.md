# TrueRecall Base (v1)

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

**Features:**
- ✅ Full context conversations saved (not just summaries)
- ✅ Automatically stripped of markdown, tables, and extra characters
- ✅ Fully searchable via semantic + exact match
- ✅ Compatible with other AI tools and agents

**Base does NOT include:**
- ❌ Curation (gem extraction)
- ❌ Topic clustering (blocks)
- ❌ Injection (context recall)

**For those features, install an addon after base.**

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

### 1. Install

```bash
cd /root/.openclaw/workspace/.local_projects/true-recall-base

# Copy service file
sudo cp watcher/mem-qdrant-watcher.service /etc/systemd/system/

# Reload and start
sudo systemctl daemon-reload
sudo systemctl enable --now mem-qdrant-watcher
```

### 2. Verify

```bash
# Check service
sudo systemctl status mem-qdrant-watcher

# Check collection (replace <QDRANT_IP> with your Qdrant IP)
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

## Next Step

Install an **addon** for curation and injection:

| Addon | Purpose |
|-------|---------|
| **Gems** | Extracts atomic gems from memories, injects into context |
| **Blocks** | Topic clustering, contextual block retrieval |

**Prerequisite for:** TrueRecall Gems, TrueRecall Blocks
