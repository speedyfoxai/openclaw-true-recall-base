#!/bin/bash
# Validation Script for openclaw-true-recall-base v1.3
# Tests all fixes and changes from v1.2 → v1.3

set -e

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║  TrueRecall Base v1.3 Validation Script                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

PASS=0
FAIL=0
WARN=0

check_pass() { echo "✅ $1"; ((PASS++)); }
check_fail() { echo "❌ $1"; ((FAIL++)); }
check_warn() { echo "⚠️  $1"; ((WARN++)); }

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1: File Structure
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 1: File Structure"
echo "═════════════════════════════════════════════════════════════════════════"

PROJECT_DIR="$(dirname "$0")"

if [ -f "$PROJECT_DIR/CHANGELOG.md" ]; then
    check_pass "CHANGELOG.md exists"
else
    check_fail "CHANGELOG.md missing"
fi

if [ -f "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py" ]; then
    check_pass "realtime_qdrant_watcher.py exists"
else
    check_fail "realtime_qdrant_watcher.py missing"
fi

# Check version in file
VERSION=$(grep -m1 "TrueRecall v" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py" | grep -oE "v[0-9]+\.[0-9]+")
if [ "$VERSION" = "v1.3" ]; then
    check_pass "Version is v1.3"
else
    check_fail "Version mismatch: expected v1.3, got $VERSION"
fi

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2: Code Changes (v1.3 Fixes)
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 2: Code Changes (v1.3 Fixes)"
echo "═════════════════════════════════════════════════════════════════════════"

# Fix 1: FileNotFoundError check
if grep -q "if not session_file.exists():" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py"; then
    check_pass "FileNotFoundError fix: Pre-check exists before open()"
else
    check_fail "FileNotFoundError fix MISSING: No session_file.exists() check"
fi

if grep -q "except FileNotFoundError:" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py"; then
    check_pass "FileNotFoundError fix: Exception handler present"
else
    check_fail "FileNotFoundError fix MISSING: No FileNotFoundError exception handler"
fi

# Fix 2: Chunking for long content
if grep -q "def chunk_text" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py"; then
    check_pass "Chunking fix: chunk_text() function defined"
else
    check_fail "Chunking fix MISSING: No chunk_text() function"
fi

if grep -q "chunk_text_content" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py"; then
    check_pass "Chunking fix: chunk_text_content used in store_to_qdrant()"
else
    check_fail "Chunking fix MISSING: Not using chunked content"
fi

if grep -q "chunk_index" "$PROJECT_DIR/watcher/realtime_qdrant_watcher.py"; then
    check_pass "Chunking fix: chunk_index metadata added"
else
    check_fail "Chunking fix MISSING: No chunk_index metadata"
fi

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3: Service Status
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 3: Service Status"
echo "═════════════════════════════════════════════════════════════════════════"

if systemctl is-active --quiet mem-qdrant-watcher 2>/dev/null; then
    check_pass "mem-qdrant-watcher service is running"
else
    check_warn "mem-qdrant-watcher service not running (may be running in daemon mode)"
fi

# Check for running watcher process
if pgrep -f "realtime_qdrant_watcher" > /dev/null; then
    check_pass "realtime_qdrant_watcher process is running"
else
    check_fail "realtime_qdrant_watcher process NOT running"
fi

# ════════════════════════════════════════════════════════════════════════════
# SECTION 4: Connectivity
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 4: Connectivity"
echo "═════════════════════════════════════════════════════════════════════════"

# Qdrant
QDRANT_URL="${QDRANT_URL:-http://10.0.0.40:6333}"
if curl -s -o /dev/null -w "%{http_code}" "$QDRANT_URL/collections/memories_tr" | grep -q "200"; then
    check_pass "Qdrant memories_tr collection reachable"
else
    check_fail "Qdrant memories_tr collection NOT reachable"
fi

# Ollama (local)
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:11434/api/tags" | grep -q "200"; then
    check_pass "Ollama (localhost) reachable"
else
    check_fail "Ollama (localhost) NOT reachable"
fi

# Check embedding model
if curl -s "http://localhost:11434/api/tags" | grep -q "snowflake-arctic-embed2"; then
    check_pass "Embedding model snowflake-arctic-embed2 available"
else
    check_fail "Embedding model snowflake-arctic-embed2 NOT available"
fi

# ════════════════════════════════════════════════════════════════════════════
# SECTION 5: Crash Loop Test
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 5: Crash Loop Test (Last 1 Hour)"
echo "═════════════════════════════════════════════════════════════════════════"

RESTARTS=$(journalctl -u mem-qdrant-watcher --since "1 hour ago" --no-pager 2>/dev/null | grep -c "Started mem-qdrant-watcher" || echo "0")
if [ "$RESTARTS" -le 2 ]; then
    check_pass "Restarts in last hour: $RESTARTS (expected ≤2)"
else
    check_fail "Restarts in last hour: $RESTARTS (too many, expected ≤2)"
fi

# Check for FileNotFoundError in logs
ERRORS=$(journalctl -u mem-qdrant-watcher --since "1 hour ago" --no-pager 2>/dev/null | grep -c "FileNotFoundError" || echo "0")
if [ "$ERRORS" -eq 0 ]; then
    check_pass "No FileNotFoundError in last hour"
else
    check_fail "FileNotFoundError found $ERRORS times in last hour"
fi

# ════════════════════════════════════════════════════════════════════════════
# SECTION 6: Chunking Test
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 6: Chunking Test"
echo "═════════════════════════════════════════════════════════════════════════"

# Test chunking with Python
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/watcher')

# Import chunk_text function
exec(open('$PROJECT_DIR/watcher/realtime_qdrant_watcher.py').read().split('def chunk_text')[1].split('def store_to_qdrant')[0])

# Test with long content
test_content = 'A' * 10000
chunks = chunk_text(test_content, max_chars=6000, overlap=200)

if len(chunks) > 1:
    print(f'PASS: chunk_text splits 10000 chars into {len(chunks)} chunks')
    sys.exit(0)
else:
    print(f'FAIL: chunk_text returned {len(chunks)} chunks for 10000 chars')
    sys.exit(1)
" 2>/dev/null && check_pass "chunk_text() splits long content correctly" || check_fail "chunk_text() test failed"

# ════════════════════════════════════════════════════════════════════════════
# SECTION 7: Git Status
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "SECTION 7: Git Status"
echo "═════════════════════════════════════════════════════════════════════════"

cd "$PROJECT_DIR"

# Check for v1.3 tag
if git tag -l | grep -q "v1.3"; then
    check_pass "Git tag v1.3 exists"
else
    check_fail "Git tag v1.3 missing"
fi

# Check CHANGELOG.md committed
if git log --oneline -1 | grep -q "v1.3"; then
    check_pass "v1.3 commit in git log"
else
    check_fail "v1.3 commit not found in git log"
fi

# Check for uncommitted changes
UNCOMMITTED=$(git status --short 2>/dev/null | wc -l)
if [ "$UNCOMMITTED" -eq 0 ]; then
    check_pass "No uncommitted changes"
else
    check_warn "$UNCOMMITTED uncommitted files"
fi

# ════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════════
echo ""
echo "═════════════════════════════════════════════════════════════════════════"
echo "VALIDATION SUMMARY"
echo "═════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Passed: $PASS"
echo "❌ Failed: $FAIL"
echo "⚠️  Warnings: $WARN"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║  ✅ ALL VALIDATIONS PASSED - v1.3 READY FOR PRODUCTION                 ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║  ❌ VALIDATION FAILED - $FAIL ISSUE(S) NEED ATTENTION                           ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    exit 1
fi