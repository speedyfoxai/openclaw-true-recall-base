# TrueRecall Base - Comprehensive Audit Checklist

**Project:** true-recall-base (Git version)  
**Location:** `/root/.openclaw/workspace/.git_projects/true-recall-base/`  
**Date:** 2026-02-27  
**Auditor:** Agent (qwen3:30b-a3b-instruct @ 10.0.0.10)  
**Status:** PENDING

---

## Audit Rules

1. **NO CHANGES** - Document only, do not modify files
2. **Read-only** - Use `read` and `exec` tools only
3. **Write results** to: `AUDIT_RESULTS_YYYYMMDD-HHMMSS.md` in this directory
4. **Be thorough** - Check every file, every path, every reference

---

## Phase 1: File Structure & Completeness

### 1.1 Root Directory Files
- [ ] List all files in root directory
- [ ] Verify expected files exist:
  - [ ] README.md
  - [ ] config.json
  - [ ] .gitignore
  - [ ] watcher/ directory
- [ ] Check for unexpected files (should not exist):
  - [ ] No session.md (should be local only)
  - [ ] No .pyc files
  - [ ] No __pycache__
  - [ ] No .env or credential files

### 1.2 Watcher Directory
- [ ] List all files in watcher/
- [ ] Verify expected files:
  - [ ] realtime_qdrant_watcher.py
  - [ ] mem-qdrant-watcher.service
- [ ] Check for unexpected files

### 1.3 Git Repository Health
- [ ] Check .git/ directory exists and is valid
- [ ] Verify no uncommitted changes: `git status`
- [ ] Check recent commits: `git log --oneline -5`
- [ ] Verify clean working tree

---

## Phase 2: README.md Audit

### 2.1 Header & Title
- [ ] Title includes "(v1)" for clarity
- [ ] Purpose statement is clear
- [ ] Status badge is accurate

### 2.2 Content Accuracy
- [ ] No duplicate sections
- [ ] "Base does NOT include:" appears only ONCE
- [ ] Three-tier architecture diagram is accurate
- [ ] Features list is correct

### 2.3 Installation Instructions
- [ ] Quick Start section exists
- [ ] Service file copy instructions are correct
- [ ] Paths use `<INSTALL_PATH>` placeholder (not hardcoded)

### 2.4 Configuration Table
- [ ] All environment variables listed
- [ ] Default values use placeholders (not real IPs)
- [ ] Description column is accurate

### 2.5 Links & References
- [ ] No broken markdown links
- [ ] File references in table are accurate
- [ ] "Next Step" section mentions Gems and Blocks addons

### 2.6 Grammar & Spelling
- [ ] Check for typos
- [ ] Check for grammatical errors
- [ ] Consistent capitalization

---

## Phase 3: Configuration Files

### 3.1 config.json
- [ ] File is valid JSON: `python3 -m json.tool config.json`
- [ ] All required fields present:
  - [ ] version
  - [ ] description
  - [ ] components
  - [ ] collections
  - [ ] qdrant_url (placeholder format)
  - [ ] ollama_url (placeholder format)
  - [ ] embedding_model
  - [ ] user_id (placeholder format)
- [ ] No real IPs or credentials
- [ ] Formatting is clean

### 3.2 .gitignore
- [ ] File exists
- [ ] Ignores appropriate patterns:
  - [ ] __pycache__/
  - [ ] *.pyc
  - [ ] .env
  - [ ] session.md (if present)

---

## Phase 4: Watcher Script Audit (realtime_qdrant_watcher.py)

### 4.1 Script Structure
- [ ] Shebang present: `#!/usr/bin/env python3`
- [ ] Docstring describes purpose
- [ ] No hardcoded credentials

### 4.2 Imports
- [ ] Only standard library + requests
- [ ] No redis import (should be Qdrant only)
- [ ] All imports used

### 4.3 Configuration Variables
- [ ] QDRANT_URL uses environment variable with fallback
- [ ] OLLAMA_URL uses environment variable with fallback
- [ ] EMBEDDING_MODEL uses environment variable with fallback
- [ ] USER_ID uses environment variable with fallback
- [ ] SESSIONS_DIR is correct path

### 4.4 Functions
- [ ] All functions have docstrings
- [ ] get_embedding() function works
- [ ] clean_content() function present
- [ ] store_turn() function present
- [ ] get_session_file() function present
- [ ] parse_turn() function present
- [ ] watch_session_file() function present

### 4.5 Error Handling
- [ ] Try/except blocks around network calls
- [ ] Graceful failure on Qdrant unavailable
- [ ] Graceful failure on Ollama unavailable

### 4.6 Security
- [ ] No hardcoded passwords
- [ ] No hardcoded API keys
- [ ] No sensitive data in comments

### 4.7 Code Quality
- [ ] No TODO or FIXME comments
- [ ] No debug print statements
- [ ] Consistent formatting

---

## Phase 5: Systemd Service Audit (mem-qdrant-watcher.service)

### 5.1 Unit Section
- [ ] Description is accurate
- [ ] After=network.target is present

### 5.2 Service Section
- [ ] Type=simple
- [ ] User=<USER> (placeholder, not hardcoded)
- [ ] WorkingDirectory uses <INSTALL_PATH> placeholder
- [ ] All Environment variables use placeholders:
  - [ ] QDRANT_URL=http://<QDRANT_IP>:6333
  - [ ] OLLAMA_URL=http://<OLLAMA_IP>:11434
  - [ ] USER_ID=<USER_ID>
- [ ] ExecStart path uses <INSTALL_PATH> placeholder
- [ ] Restart=always present
- [ ] RestartSec=5 present

### 5.3 Install Section
- [ ] WantedBy=multi-user.target present

### 5.4 No Redis References
- [ ] No mention of redis in service file
- [ ] No redis-server.service in After=

---

## Phase 6: Path & Reference Verification

### 6.1 No Wrong Project References
- [ ] No references to "true-recall-v1"
- [ ] No references to "true-recall-v2"
- [ ] No references to "mem-redis"
- [ ] All paths reference "true-recall-base"

### 6.2 Cross-File Consistency
- [ ] README mentions same files as exist
- [ ] Service file references correct script name
- [ ] Config.json matches README table

### 6.3 Documentation Accuracy
- [ ] File table in README matches actual files
- [ ] Installation steps are accurate
- [ ] Verification commands work

---

## Phase 7: Security Audit

### 7.1 Credential Scan
- [ ] Search for "password" in all files
- [ ] Search for "token" in all files
- [ ] Search for "secret" in all files
- [ ] Search for "api_key" in all files
- [ ] Search for IP addresses (should only be placeholders)

### 7.2 File Permissions
- [ ] No executable .py files (should be 644)
- [ ] .service file permissions appropriate
- [ ] No world-writable files

### 7.3 Sensitive Data
- [ ] No .env files
- [ ] No .pem or .key files
- [ ] No credentials.json

---

## Phase 8: Dependencies & Compatibility

### 8.1 Python Requirements
- [ ] List all imports in watcher script
- [ ] Verify they're standard library or common packages:
  - [ ] os, sys, json, time, signal, hashlib, argparse
  - [ ] requests (external)
  - [ ] datetime, pathlib, typing
- [ ] No unusual dependencies

### 8.2 External Services
- [ ] Qdrant reference is correct
- [ ] Ollama reference is correct
- [ ] Both use configurable URLs

### 8.3 Platform Compatibility
- [ ] Uses /usr/bin/python3 (standard)
- [ ] Systemd service format is standard
- [ ] Paths use forward slashes (Unix compatible)

---

## Phase 9: Documentation Completeness

### 9.1 README Sections Present
- [ ] Title/Purpose
- [ ] Overview
- [ ] Features
- [ ] Architecture diagram
- [ ] Quick Start (Install + Verify)
- [ ] Files table
- [ ] Configuration table
- [ ] Next Step

### 9.2 Missing Documentation
- [ ] No TODO items
- [ ] No "coming soon" sections
- [ ] No incomplete sentences

---

## Phase 10: Final Verification

### 10.1 Git Status
- [ ] Working tree clean: `git status`
- [ ] No uncommitted changes
- [ ] No untracked files that should be tracked

### 10.2 Compare Local vs Git
- [ ] Structure matches local project
- [ ] Files are equivalent (sanitized)
- [ ] No extra files in git

### 10.3 Overall Assessment
- [ ] Project is ready for distribution
- [ ] No blockers
- [ ] Documentation is complete

---

## Output Requirements

Write detailed findings to: `AUDIT_RESULTS_20260227-HHMMSS.md`

Include:
1. **Executive Summary** - Overall status (PASS/FAIL)
2. **Phase-by-phase results** - Detailed findings per section
3. **Issues Found** - Categorized by severity:
   - 🔴 Critical - Must fix before release
   - 🟠 High - Should fix soon
   - 🟡 Medium - Nice to have
   - 🟢 Low - Minor suggestions
4. **Action Items** - Specific recommendations
5. **Sign-off** - Auditor confirmation

---

## Audit Completion Criteria

- [ ] All 10 phases completed
- [ ] Results file written
- [ ] No unchecked boxes
- [ ] Clear pass/fail determination

**Begin audit now. Report findings when complete.**
