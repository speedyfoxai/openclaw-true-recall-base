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

# Check collection
curl -s http://10.0.0.40:6333/collections/memories_tr | jq '.result.points_count'
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
| `QDRANT_URL` | `http://10.0.0.40:6333` | Qdrant endpoint |
| `OLLAMA_URL` | `http://10.0.0.10:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | `snowflake-arctic-embed2` | Embedding model |
| `USER_ID` | `rob` | User identifier |

---

## Next Step

Install **TrueRecall v2** for curation and injection:

```bash
# v2 adds:
# - Curator (extracts gems from memories)
# - Injection (recalls gems into context)
```

v2 requires Base to be running first.

**Prerequisite for:** TrueRecall v2
