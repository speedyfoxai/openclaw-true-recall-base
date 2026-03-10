#!/usr/bin/env python3
"""Backfill memory files to Qdrant memories_tr collection."""

import os
import json
from datetime import datetime

QDRANT_URL = "http://10.0.0.40:6333"
MEMORY_DIR = "/root/.openclaw/workspace/memory"

def get_memory_files():
    """Get all memory files sorted by date."""
    files = []
    for f in os.listdir(MEMORY_DIR):
        if f.startswith("2026-") and f.endswith(".md"):
            date = f.replace(".md", "")
            files.append((date, f))
    return sorted(files, key=lambda x: x[0])

def backfill_file(date, filename):
    """Backfill a single memory file to Qdrant."""
    filepath = os.path.join(MEMORY_DIR, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Truncate if too long for payload
    payload = {
        "content": content[:50000],  # Limit size
        "date": date,
        "source": "memory_file",
        "curated": False,
        "role": "system",
        "user_id": "rob"
    }
    
    # Add to Qdrant
    import requests
    point_id = hash(f"memory_{date}") % 10000000000
    resp = requests.post(
        f"{QDRANT_URL}/collections/memories_tr/points",
        json={
            "points": [{
                "id": point_id,
                "payload": payload
            }],
            "ids": [point_id]
        }
    )
    return resp.status_code == 200

def main():
    files = get_memory_files()
    print(f"Found {len(files)} memory files to backfill")
    
    count = 0
    for date, filename in files:
        print(f"Backfilling {filename}...", end=" ")
        if backfill_file(date, filename):
            print("✓")
            count += 1
        else:
            print("✗")
    
    print(f"\nBackfilled {count}/{len(files)} files")

if __name__ == "__main__":
    main()
