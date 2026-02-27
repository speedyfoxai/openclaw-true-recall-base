# TrueRecall Base - Session Notes

**Last Updated:** 2026-02-26 14:00 CST
**Status:** ✅ Foundation operational
**Version:** v1.0

---

## Architecture Overview

TrueRecall uses a **three-tier architecture**:

```
true-recall-base (REQUIRED FOUNDATION)
├── Watcher daemon (real-time capture)
└── Collection: memories_tr
    │
    ├──▶ true-recall-gems (OPTIONAL ADDON)
    │   ├── Curator extracts atomic gems
    │   └── Plugin injects gems as context
    │
    └──▶ true-recall-blocks (OPTIONAL ADDON)
        ├── Topic clustering
        └── Block-based retrieval
```

### Important: Gems and Blocks are INDEPENDENT

- ✅ Base is **required** by both
- ✅ Choose **Gems** OR **Blocks** (not both)
- ❌ They do NOT work together
- ❌ Don't install both addons

---

## What Base Provides

| Feature | Description |
|---------|-------------|
| Real-time capture | Every conversation turn saved |
| memories_tr | Qdrant collection for raw memories |
| Embeddings | snowflake-arctic-embed2 @ 1024 dims |
| Deduplication | Content hash prevents duplicates |
| User tagging | All memories tagged with user_id |

---

## Prerequisites for Addons

Before installing Gems or Blocks:

```bash
# Verify base is running
sudo systemctl status mem-qdrant-watcher

# Check memories_tr exists
curl -s http://10.0.0.40:6333/collections/memories_tr | jq '.result.status'

# Verify points are being added
curl -s http://10.0.0.40:6333/collections/memories_tr | jq '.result.points_count'
```

---

## Choosing Your Addon

| Addon | Best For | Storage |
|-------|----------|---------|
| **Gems** | Quick fact retrieval, atomic insights | gems_tr |
| **Blocks** | Contextual topic recall, full context | topic_blocks_tr |

**Don't mix:** Installing both creates redundant systems.

---

## Current State

- Service: mem-qdrant-watcher ✅ Active
- Collection: memories_tr ✅ Green
- Embeddings: snowflake-arctic-embed2 ✅
- Points: Growing continuously

---

*Next: Install true-recall-gems OR true-recall-blocks (not both)*
