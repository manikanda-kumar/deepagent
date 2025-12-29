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

# Create dedicated user for orchestrator
echo "Creating deepagent user..."
useradd -r -m -s /bin/bash deepagent || true

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

# Clone deepagent monorepo
echo "Setting up DeepAgent..."
if [ ! -d "/app/deepagent" ]; then
    git clone ${DEEPAGENT_REPO_URL:-https://github.com/YOUR_USERNAME/deepagent.git} /app/deepagent
fi
chown -R deepagent:deepagent /app/deepagent

# Setup orchestrator as deepagent user
echo "Setting up orchestrator..."
su - deepagent -c "
cd /app/deepagent/orchestrator
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
"

# Symlink pi-skills into claude/ directory
echo "Symlinking pi-skills..."
mkdir -p /app/deepagent/claude/skills
for skill in browser-tools gdcli gmcli brave-search youtube-transcript transcribe; do
    if [ -d "/opt/pi-skills/$skill" ]; then
        ln -sf /opt/pi-skills/$skill /app/deepagent/claude/skills/
        echo "  Linked $skill"
    fi
done

# Setup persistence directories with proper permissions
echo "Setting up persistence directories..."
mkdir -p /data/{db,outputs,logs,tokens}
chown -R deepagent:deepagent /data
chmod 700 /data/db /data/tokens
chmod 755 /data/outputs /data/logs

# Create secrets directory
echo "Setting up secrets..."
mkdir -p /etc/deepagent
cat > /etc/deepagent/env << 'EOF'
# DeepAgent Environment Variables
# Add your secrets here

# Required
DATABASE_URL=sqlite:////data/db/deepagent.db
CLAUDE_PATH=/app/deepagent/claude
OUTPUTS_PATH=/data/outputs
SKILLS_PATH=/app/deepagent/claude/skills

# API Security
# API_SECRET_KEY=your-secret-key-here

# Claude Code
# ANTHROPIC_API_KEY=sk-ant-...

# Brave Search
# BRAVE_API_KEY=...

# Firebase (Push Notifications)
# FIREBASE_PROJECT_ID=...
# FIREBASE_CREDENTIALS_PATH=/data/firebase-credentials.json
EOF
chmod 600 /etc/deepagent/env
chown deepagent:deepagent /etc/deepagent/env

# Configure systemd service
echo "Configuring systemd service..."
cat > /etc/systemd/system/deepagent.service << 'EOF'
[Unit]
Description=DeepAgent Orchestrator
After=network.target

[Service]
Type=simple
User=deepagent
Group=deepagent
WorkingDirectory=/app/deepagent/orchestrator
EnvironmentFile=/etc/deepagent/env
ExecStart=/app/deepagent/orchestrator/venv/bin/uvicorn api.routes:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/data

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
echo "  1. Edit secrets: nano /etc/deepagent/env"
echo "  2. Run OAuth setup: su - deepagent -c '/app/deepagent/scripts/setup-oauth.sh'"
echo "  3. Restart service: systemctl restart deepagent"
echo "  4. Expose API: labctl expose port 8000 --https"
echo ""
