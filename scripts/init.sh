#!/bin/bash
set -e

echo "=== DeepAgent VM Initialization ==="

# System dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    nodejs npm \
    chromium-browser \
    git curl jq

# Install Claude Code CLI
echo "Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Install onedrive-cli
echo "Installing onedrive-cli..."
pip install onedrive-cli

# Clone pi-skills
echo "Cloning pi-skills..."
if [ ! -d "/opt/pi-skills" ]; then
    git clone https://github.com/badlogic/pi-skills.git /opt/pi-skills
    cd /opt/pi-skills && npm install
fi

# Setup browser-tools Chrome profile
echo "Setting up browser-tools..."
if [ -f "/opt/pi-skills/browser-tools/setup.sh" ]; then
    /opt/pi-skills/browser-tools/setup.sh
fi

# Clone deepagent monorepo (if not already present)
echo "Setting up DeepAgent..."
if [ ! -d "/app/deepagent" ]; then
    git clone ${DEEPAGENT_REPO_URL:-https://github.com/YOUR_USERNAME/deepagent.git} /app/deepagent
fi

# Setup orchestrator
echo "Setting up orchestrator..."
cd /app/deepagent/orchestrator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Symlink pi-skills into claude/ directory
echo "Symlinking pi-skills..."
mkdir -p /app/deepagent/claude/skills
for skill in browser-tools gdcli gmcli brave-search youtube-transcript transcribe; do
    if [ -d "/opt/pi-skills/$skill" ]; then
        ln -sf /opt/pi-skills/$skill /app/deepagent/claude/skills/
        echo "  Linked $skill"
    fi
done

# Setup persistence directories
echo "Setting up persistence directories..."
mkdir -p /data/{db,outputs,logs,tokens}
chown -R root:root /data

# Configure systemd service
echo "Configuring systemd service..."
cat > /etc/systemd/system/deepagent.service << 'EOF'
[Unit]
Description=DeepAgent Orchestrator
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/app/deepagent/orchestrator
ExecStart=/app/deepagent/orchestrator/venv/bin/uvicorn api.routes:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Environment
Environment=DATABASE_URL=sqlite:////data/db/deepagent.db
Environment=CLAUDE_PATH=/app/deepagent/claude
Environment=OUTPUTS_PATH=/data/outputs
Environment=SKILLS_PATH=/app/deepagent/claude/skills

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable deepagent
systemctl start deepagent

echo ""
echo "=== DeepAgent initialized successfully! ==="
echo ""
echo "Next steps:"
echo "  1. Run: /app/deepagent/scripts/setup-oauth.sh"
echo "  2. Expose API: labctl expose port 8000 --https"
echo ""
