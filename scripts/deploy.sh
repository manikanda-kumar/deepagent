#!/bin/bash
set -e

echo "=== DeepAgent Deployment ==="

# Pull latest changes
echo "Pulling latest changes..."
cd /app/deepagent
git pull origin main

# Update orchestrator dependencies
echo "Updating orchestrator dependencies..."
cd /app/deepagent/orchestrator
source venv/bin/activate
pip install -r requirements.txt

# Restart service
echo "Restarting service..."
systemctl restart deepagent

# Wait and check status
sleep 3
echo ""
echo "Service status:"
systemctl status deepagent --no-pager

echo ""
echo "=== Deployment complete! ==="
