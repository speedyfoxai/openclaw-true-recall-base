#!/bin/bash

# search_q.sh - Search memories with chronological sorting
# Usage: ./search_q.sh "search query"
# Returns: Results sorted by timestamp (newest first)

set -e

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
COLLECTION="${QDRANT_COLLECTION:-memories_tr}"
LIMIT="${SEARCH_LIMIT:-10}"

if [ -z "$1" ]; then
    echo "Usage: ./search_q.sh 'your search query'"
    echo ""
    echo "Environment variables:"
    echo "  QDRANT_URL      - Qdrant endpoint (default: http://localhost:6333)"
    echo "  SEARCH_LIMIT    - Number of results (default: 10)"
    exit 1
fi

QUERY="$1"

echo "=========================================="
echo "Searching: '$QUERY'"
echo "=========================================="
echo ""

# Search with scroll to get all results, then sort by timestamp
# Using scroll API to handle large result sets
SCROLL_ID="null"
ALL_RESULTS="[]"

while true; do
    if [ "$SCROLL_ID" = "null" ]; then
        RESPONSE=$(curl -s -X POST "$QDRANT_URL/collections/$COLLECTION/points/scroll" \
            -H "Content-Type: application/json" \
            -d "{
                \"limit\": $LIMIT,
                \"with_payload\": true,
                \"filter\": {
                    \"must\": [
                        {
                            \"key\": \"content\",
                            \"match\": {
                                \"text\": \"$QUERY\"
                            }
                        }
                    ]
                }
            }") 2>/dev/null || echo '{"result": {"points": []}}'
    else
        break  # For text search, we get results in first call
    fi
    
    # Extract results
    POINTS=$(echo "$RESPONSE" | jq -r '.result.points // []')
    
    if [ "$POINTS" = "[]" ] || [ "$POINTS" = "null" ]; then
        break
    fi
    
    ALL_RESULTS="$POINTS"
    break
done

# Sort by timestamp (newest first) and format output
echo "$ALL_RESULTS" | jq -r '
    sort_by(.payload.timestamp) | reverse | 
    .[] | 
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
    "📅 " + (.payload.timestamp | split("T") | join(" ")) + "\n" +
    "👤 " + .payload.role + "\n" +
    "📝 " + (.payload.content | if length > 200 then .[0:200] + "..." else . end) + "\n"
' 2>/dev/null || echo "No results found for '$QUERY'"

echo ""
echo "=========================================="
echo "Search complete. Most recent results shown first."
echo "=========================================="
