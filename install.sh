#!/bin/bash

# TrueRecall Base - Simple Installer
# Usage: ./install.sh

set -e

echo "=========================================="
echo "TrueRecall Base - Installer"
echo "=========================================="
echo ""

# Default values
DEFAULT_QDRANT_IP="localhost:6333"
DEFAULT_OLLAMA_IP="localhost:11434"
DEFAULT_USER_ID="user"

# Get user input with defaults
echo "Configuration (press Enter for defaults):"
echo ""
echo "Examples:"
echo "  Qdrant:  10.0.0.40:6333  (remote)  or  localhost:6333  (local)"
echo "  Ollama:  10.0.0.10:11434 (remote)  or  localhost:11434 (local)"
echo ""

read -p "Qdrant host:port [$DEFAULT_QDRANT_IP]: " QDRANT_IP
QDRANT_IP=${QDRANT_IP:-$DEFAULT_QDRANT_IP}

read -p "Ollama host:port [$DEFAULT_OLLAMA_IP]: " OLLAMA_IP
OLLAMA_IP=${OLLAMA_IP:-$DEFAULT_OLLAMA_IP}

read -p "User ID [$DEFAULT_USER_ID]: " USER_ID
USER_ID=${USER_ID:-$DEFAULT_USER_ID}

echo ""
echo "Configuration:"
echo "  Qdrant: http://$QDRANT_IP"
echo "  Ollama: http://$OLLAMA_IP"
echo "  User ID: $USER_ID"
echo ""

read -p "Proceed? [Y/n]: " CONFIRM
if [[ $CONFIRM =~ ^[Nn]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Create service file
echo ""
echo "Creating systemd service..."

# Get absolute path (handles spaces)
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cat > /tmp/mem-qdrant-watcher.service << EOF
[Unit]
Description=TrueRecall Base - Real-Time Memory Watcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/watcher
Environment="QDRANT_URL=http://$QDRANT_IP"
Environment="QDRANT_COLLECTION=memories_tr"
Environment="OLLAMA_URL=http://$OLLAMA_IP"
Environment="EMBEDDING_MODEL=snowflake-arctic-embed2"
Environment="USER_ID=$USER_ID"
ExecStart=/usr/bin/python3 $INSTALL_DIR/watcher/realtime_qdrant_watcher.py --daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Install service
sudo cp /tmp/mem-qdrant-watcher.service /etc/systemd/system/
sudo systemctl daemon-reload

echo ""
echo "Starting service..."
sudo systemctl enable --now mem-qdrant-watcher

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Status:"
sudo systemctl status mem-qdrant-watcher --no-pager

echo ""
echo "Verify collection:"
echo "  curl -s http://$QDRANT_IP/collections/memories_tr | jq '.result.points_count'"
echo ""
echo "View logs:"
echo "  sudo journalctl -u mem-qdrant-watcher -f"
