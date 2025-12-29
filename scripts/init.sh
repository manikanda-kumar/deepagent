#!/bin/bash
set -e

echo "=== DeepAgent VM Initialization ==="
echo "Started at: $(date)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# System dependencies
echo ""
echo "[1/8] Installing system dependencies..."
apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    nodejs npm \
    chromium-browser \
    git curl jq

# Detect Python version
PYTHON_CMD=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &> /dev/null; then
        PYTHON_CMD="$py"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: No suitable Python 3 found"
    exit 1
fi
echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# Create dedicated user for orchestrator
echo ""
echo "[2/8] Creating deepagent user..."
if id "deepagent" &>/dev/null; then
    echo "User deepagent already exists"
else
    useradd -r -m -s /bin/bash deepagent
    echo "User deepagent created"
fi

# Install Claude Code CLI
echo ""
echo "[3/8] Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# Install onedrive-cli
echo ""
echo "[4/8] Installing onedrive-cli..."
pip3 install onedrive-cli

# Clone pi-skills
echo ""
echo "[5/8] Setting up pi-skills..."
if [ ! -d "/opt/pi-skills" ]; then
    git clone https://github.com/badlogic/pi-skills.git /opt/pi-skills
    cd /opt/pi-skills && npm install
    echo "pi-skills installed"
else
    echo "pi-skills already exists, updating..."
    cd /opt/pi-skills && git pull && npm install
fi

# Setup browser-tools Chrome profile
if [ -f "/opt/pi-skills/browser-tools/setup.sh" ]; then
    echo "Setting up browser-tools Chrome profile..."
    /opt/pi-skills/browser-tools/setup.sh || echo "Warning: browser-tools setup failed (may need manual setup)"
fi

# Clone deepagent monorepo
echo ""
echo "[6/8] Setting up DeepAgent application..."
REPO_URL="${DEEPAGENT_REPO_URL:-https://github.com/laborant/deepagent.git}"
if [ ! -d "/app/deepagent" ]; then
    echo "Cloning from $REPO_URL..."
    mkdir -p /app
    git clone "$REPO_URL" /app/deepagent
else
    echo "DeepAgent already exists, pulling latest..."
    cd /app/deepagent && git pull origin main || echo "Warning: git pull failed"
fi
chown -R deepagent:deepagent /app/deepagent

# Setup orchestrator as deepagent user
echo "Setting up Python virtual environment..."
su - deepagent -c "
cd /app/deepagent/orchestrator
$PYTHON_CMD -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
"
echo "Orchestrator dependencies installed"

# Symlink pi-skills into claude/ directory
echo ""
echo "[7/8] Linking pi-skills to Claude directory..."
mkdir -p /app/deepagent/claude/skills
LINKED_SKILLS=""
for skill in browser-tools gdcli gmcli brave-search youtube-transcript transcribe; do
    if [ -d "/opt/pi-skills/$skill" ]; then
        ln -sf /opt/pi-skills/$skill /app/deepagent/claude/skills/
        LINKED_SKILLS="$LINKED_SKILLS $skill"
    fi
done
echo "Linked skills:$LINKED_SKILLS"

# Setup persistence directories with proper permissions
echo ""
echo "[8/8] Setting up persistence directories and configuration..."
mkdir -p /data/{db,outputs,logs,tokens}
chown -R deepagent:deepagent /data
chmod 700 /data/db /data/tokens
chmod 755 /data/outputs /data/logs
echo "Created /data directories with proper permissions"

# Create secrets directory and env file (only if doesn't exist)
mkdir -p /etc/deepagent
if [ ! -f "/etc/deepagent/env" ]; then
    cat > /etc/deepagent/env << 'EOF'
# DeepAgent Environment Variables
# Edit this file and add your API keys

# Database (required - default works for local SQLite)
DATABASE_URL=sqlite+aiosqlite:////data/db/deepagent.db

# Paths (required - defaults match VM deployment)
CLAUDE_PATH=/app/deepagent/claude
OUTPUTS_PATH=/data/outputs
SKILLS_PATH=/app/deepagent/claude/skills

# API Security (generate a random key for production)
# API_SECRET_KEY=your-secret-key-here

# Claude Code (required for task execution)
# ANTHROPIC_API_KEY=sk-ant-...

# Brave Search (required for web search tasks)
# BRAVE_API_KEY=...

# Groq (optional - for audio transcription)
# GROQ_API_KEY=...

# Firebase (optional - for push notifications)
# FIREBASE_PROJECT_ID=...
# FIREBASE_CREDENTIALS_PATH=/data/firebase-credentials.json
EOF
    echo "Created /etc/deepagent/env template"
else
    echo "/etc/deepagent/env already exists, preserving existing configuration"
fi
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
WorkingDirectory=/app/deepagent
EnvironmentFile=/etc/deepagent/env
Environment=PYTHONPATH=/app/deepagent
ExecStart=/app/deepagent/orchestrator/venv/bin/uvicorn orchestrator.main:app --host 0.0.0.0 --port 8000
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

# Don't start service yet - user needs to configure secrets first
echo "Systemd service configured (not started - configure secrets first)"

echo ""
echo "=========================================="
echo "=== DeepAgent initialized successfully ==="
echo "=========================================="
echo ""
echo "Installation Summary:"
echo "  - Python: $PYTHON_CMD"
echo "  - App directory: /app/deepagent"
echo "  - Data directory: /data"
echo "  - Config file: /etc/deepagent/env"
echo "  - Service: deepagent.service"
echo ""
echo "Next steps:"
echo ""
echo "  1. Add your API keys to /etc/deepagent/env:"
echo "     sudo nano /etc/deepagent/env"
echo "     # Required: ANTHROPIC_API_KEY"
echo "     # Optional: BRAVE_API_KEY, GROQ_API_KEY"
echo ""
echo "  2. Run OAuth setup for cloud services:"
echo "     su - deepagent -c '/app/deepagent/scripts/setup-oauth.sh'"
echo ""
echo "  3. Start the service:"
echo "     sudo systemctl start deepagent"
echo "     sudo systemctl status deepagent"
echo ""
echo "  4. Expose API (for remote access):"
echo "     labctl expose port 8000 --https"
echo ""
echo "  5. Test the API:"
echo "     curl http://localhost:8000/api/v1/health"
echo ""
echo "Finished at: $(date)"
