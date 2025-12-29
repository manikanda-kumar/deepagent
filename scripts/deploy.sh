#!/bin/bash
set -e

echo "=== DeepAgent Deployment Update ==="
echo "Started at: $(date)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (or with sudo)"
    exit 1
fi

# Check if app directory exists
if [ ! -d "/app/deepagent" ]; then
    echo "Error: /app/deepagent not found. Run init.sh first."
    exit 1
fi

# Pull latest changes
echo ""
echo "[1/4] Pulling latest changes..."
cd /app/deepagent
sudo -u deepagent git fetch origin
CURRENT=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$CURRENT" = "$REMOTE" ]; then
    echo "Already up to date."
else
    sudo -u deepagent git pull origin main
    echo "Updated from $CURRENT to $REMOTE"
fi

# Update orchestrator dependencies
echo ""
echo "[2/4] Checking for dependency updates..."
cd /app/deepagent/orchestrator
if [ -f "requirements.txt" ]; then
    sudo -u deepagent bash -c "source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt"
    echo "Dependencies updated"
fi

# Update pi-skills
echo ""
echo "[3/4] Updating pi-skills..."
if [ -d "/opt/pi-skills" ]; then
    cd /opt/pi-skills
    git pull origin main || echo "Warning: pi-skills update failed"
    npm install --quiet || echo "Warning: npm install failed"
    echo "pi-skills updated"
else
    echo "pi-skills not found, skipping"
fi

# Restart service
echo ""
echo "[4/4] Restarting service..."
systemctl restart deepagent

# Wait and check status
sleep 3
echo ""
echo "Service status:"
systemctl status deepagent --no-pager || true

# Health check
echo ""
echo "Health check:"
sleep 2
curl -s http://localhost:8000/api/v1/health || echo "Warning: Health check failed (service may still be starting)"

echo ""
echo "=========================================="
echo "=== Deployment complete! ==="
echo "=========================================="
echo "Finished at: $(date)"
