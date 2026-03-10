# Changelog - openclaw-true-recall-base

All notable changes to this project will be documented in this file.

## [v1.3] - 2026-03-10

### Fixed

#### Critical: Crash Loop on Deleted Session Files

**Error:** `FileNotFoundError: [Errno 2] No such file or directory: '/root/.openclaw/agents/main/sessions/daccff90-f889-44fa-ba8b-c8d7397e5241.jsonl'`

**Root Cause:**
- OpenClaw deletes session `.jsonl` files when `/new` or `/reset` is called
- The watcher opened the file before checking existence
- Between file detection and opening, the file was deleted
- This caused unhandled `FileNotFoundError` → crash → systemd restart

**Impact:** 2,551 restarts in 24 hours

**Original Code (v1.2):**
```python
# Track file handle for re-opening
f = open(session_file, 'r')  # CRASH HERE if file deleted
f.seek(last_position)

try:
    while running:
        if not session_file.exists():  # Check happens AFTER crash
            ...
```

**Fix (v1.3):**
```python
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
```

#### Embedding Token Overflow

**Error:** `Ollama API error 400: {"StatusCode":400,"Status":"400 Bad Request","error":"prompt too long; exceeded max context length by 4 tokens"}`

**Root Cause:**
- The embedding model `snowflake-arctic-embed2` has a 4,096 token limit (~16K chars)
- Long messages were sent to embedding without truncation
- The watcher's `get_embedding()` call passed full `turn['content']`

**Impact:** Failed embedding generation, memory loss for long messages

**Fix:**
- Added `chunk_text()` function to split long content into 6,000 char overlapping chunks
- Each chunk gets its own Qdrant point with `chunk_index` and `total_chunks` metadata
- Overlap (200 chars) ensures search continuity
- No data loss - all content stored

### Changed

- `store_to_qdrant()` now handles multiple chunks per turn
- Each chunk stored with metadata: `chunk_index`, `total_chunks`, `full_content_length`

---

## [v1.2] - 2026-02-26

### Fixed

- Session rotation bug - added inactivity detection (30s threshold)
- Improved file scoring to properly detect new sessions on `/new` or `/reset`

---

## [v1.1] - 2026-02-25

### Added

- 1-second mtime polling for session rotation

---

## [v1.0] - 2026-02-24

### Added

- Initial release
- Real-time monitoring of OpenClaw sessions
- Automatic embedding via local Ollama (snowflake-arctic-embed2)
- Storage to Qdrant `memories_tr` collection