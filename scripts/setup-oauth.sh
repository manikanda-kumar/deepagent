#!/bin/bash
set -e

ENV_FILE="/etc/deepagent/env"

echo "=== DeepAgent OAuth & API Key Setup ==="
echo ""

# Check if running as deepagent user or root
if [ "$EUID" -eq 0 ]; then
    echo "Note: Running as root. OAuth tokens will be stored for deepagent user."
fi

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found. Run init.sh first."
    exit 1
fi

# Check if pi-skills is installed
if [ ! -d "/opt/pi-skills" ]; then
    echo "Warning: pi-skills not found at /opt/pi-skills"
    echo "Some OAuth setups may fail."
fi

# Helper function to update env file
update_env() {
    local key="$1"
    local value="$2"
    local file="$ENV_FILE"

    # Remove any existing line (commented or not)
    sudo sed -i "/^#*\s*${key}=/d" "$file"

    # Add the new value
    echo "${key}=${value}" | sudo tee -a "$file" > /dev/null
    echo "  Updated $key in $file"
}

echo "This script will help you configure:"
echo "  1. Anthropic API key (required for Claude Code)"
echo "  2. Brave Search API key (for web search)"
echo "  3. Google Drive OAuth (for file uploads)"
echo "  4. Gmail OAuth (for notifications)"
echo "  5. OneDrive OAuth (for file uploads)"
echo ""

# ============================================
# 1. Anthropic API Key
# ============================================
echo "----------------------------------------"
echo "1. Anthropic API Key"
echo "----------------------------------------"
echo "Get your API key from: https://console.anthropic.com/"
read -p "Enter your Anthropic API key (or press Enter to skip): " ANTHROPIC_KEY

if [ -n "$ANTHROPIC_KEY" ]; then
    update_env "ANTHROPIC_API_KEY" "$ANTHROPIC_KEY"
else
    echo "  Skipping Anthropic API key"
fi
echo ""

# ============================================
# 2. Brave Search API Key
# ============================================
echo "----------------------------------------"
echo "2. Brave Search API Key"
echo "----------------------------------------"
echo "Get your API key from: https://brave.com/search/api/"
read -p "Enter your Brave Search API key (or press Enter to skip): " BRAVE_KEY

if [ -n "$BRAVE_KEY" ]; then
    update_env "BRAVE_API_KEY" "$BRAVE_KEY"
else
    echo "  Skipping Brave Search API key"
fi
echo ""

# ============================================
# 3. Google Drive OAuth
# ============================================
echo "----------------------------------------"
echo "3. Google Drive OAuth"
echo "----------------------------------------"
if command -v gdcli &> /dev/null || [ -f "/opt/pi-skills/gdcli/gdcli" ]; then
    echo "This will open a browser for Google OAuth authentication."
    read -p "Press Enter to continue (or Ctrl+C to skip)..."

    if [ -f "/opt/pi-skills/gdcli/gdcli" ]; then
        sudo -u deepagent /opt/pi-skills/gdcli/gdcli auth login || echo "  Warning: gdcli auth failed"
    else
        sudo -u deepagent gdcli auth login || echo "  Warning: gdcli auth failed"
    fi
    echo "  Google Drive authentication attempted"
else
    echo "  gdcli not found, skipping"
fi
echo ""

# ============================================
# 4. Gmail OAuth
# ============================================
echo "----------------------------------------"
echo "4. Gmail OAuth"
echo "----------------------------------------"
if command -v gmcli &> /dev/null || [ -f "/opt/pi-skills/gmcli/gmcli" ]; then
    echo "This will open a browser for Gmail OAuth authentication."
    read -p "Press Enter to continue (or Ctrl+C to skip)..."

    if [ -f "/opt/pi-skills/gmcli/gmcli" ]; then
        sudo -u deepagent /opt/pi-skills/gmcli/gmcli auth login || echo "  Warning: gmcli auth failed"
    else
        sudo -u deepagent gmcli auth login || echo "  Warning: gmcli auth failed"
    fi
    echo "  Gmail authentication attempted"
else
    echo "  gmcli not found, skipping"
fi
echo ""

# ============================================
# 5. OneDrive OAuth
# ============================================
echo "----------------------------------------"
echo "5. OneDrive OAuth"
echo "----------------------------------------"
if command -v onedrive &> /dev/null; then
    echo "This will open a browser for OneDrive OAuth authentication."
    read -p "Press Enter to continue (or Ctrl+C to skip)..."

    sudo -u deepagent onedrive login || echo "  Warning: onedrive auth failed"
    echo "  OneDrive authentication attempted"
else
    echo "  onedrive-cli not found, skipping"
fi
echo ""

# ============================================
# 6. Optional: Groq API Key
# ============================================
echo "----------------------------------------"
echo "6. Groq API Key (optional - for audio transcription)"
echo "----------------------------------------"
echo "Get your API key from: https://console.groq.com/"
read -p "Enter your Groq API key (or press Enter to skip): " GROQ_KEY

if [ -n "$GROQ_KEY" ]; then
    update_env "GROQ_API_KEY" "$GROQ_KEY"
else
    echo "  Skipping Groq API key"
fi
echo ""

# ============================================
# Summary
# ============================================
echo "=========================================="
echo "=== OAuth setup complete! ==="
echo "=========================================="
echo ""
echo "Configuration saved to: $ENV_FILE"
echo ""

# Check what's configured
echo "Configured services:"
grep -E "^[A-Z_]+=" "$ENV_FILE" 2>/dev/null | grep -v "^#" | cut -d= -f1 | while read key; do
    echo "  - $key"
done

echo ""
echo "To start/restart the DeepAgent service:"
echo "  sudo systemctl restart deepagent"
echo "  sudo systemctl status deepagent"
echo ""
