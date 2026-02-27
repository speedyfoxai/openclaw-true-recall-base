#!/bin/bash

# TrueRecall Base - Simple Installer
# Usage: ./install.sh

set -e

echo "=========================================="
echo "TrueRecall Base - Installer"
echo "=========================================="
echo ""

# Default values
DEFAULT_QDRANT_IP="localhost"
DEFAULT_OLLAMA_IP="localhost"
DEFAULT_USER_ID="user"

# Get user input with defaults
echo "Configuration (press Enter for defaults):"
echo ""

read -p "Qdrant IP [$DEFAULT_QDRANT_IP]: " QDRANT_IP
QDRANT_IP=${QDRANT_IP:-$DEFAULT_QDRANT_IP}

read -p "Ollama IP [$DEFAULT_OLLAMA_IP]: " OLLAMA_IP
OLLAMA_IP=${OLLAMA_IP:-$DEFAULT_OLLAMA_IP}

read -p "User ID [$DEFAULT_USER_ID]: " USER_ID
USER_ID=${USER_ID:-$DEFAULT_USER_ID}

echo ""
echo "Configuration:"
echo "  Qdrant: http://$QDRANT_IP:6333"
echo "  Ollama: http://$OLLAMA_IP:11434"
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

cat > /tmp/mem-qdrant-watcher.service << EOF
[Unit]
Description=TrueRecall Base - Real-Time Memory Watcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/watcher
Environment="QDRANT_URL=http://$QDRANT_IP:6333"
Environment="QDRANT_COLLECTION=memories_tr"
Environment="OLLAMA_URL=http://$OLLAMA_IP:11434"
Environment="EMBEDDING_MODEL=snowflake-arctic-embed2"
Environment="USER_ID=$USER_ID"
ExecStart=/usr/bin/python3 $(pwd)/watcher/realtime_qdrant_watcher.py --daemon
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
echo "  curl -s http://$QDRANT_IP:6333/collections/memories_tr | jq '.result.points_count'"
echo ""
echo "View logs:"
echo "  sudo journalctl -u mem-qdrant-watcher -f"
