#!/bin/bash
set -e

echo "=== DeepAgent OAuth Setup ==="
echo ""

# Check if running on VM
if [ ! -d "/opt/pi-skills" ]; then
    echo "Error: pi-skills not found. Run this script on the VM after init.sh"
    exit 1
fi

# Google Drive
echo "1. Authenticating Google Drive..."
echo "   This will open a browser for OAuth authentication."
read -p "   Press Enter to continue..."
if command -v gdcli &> /dev/null; then
    gdcli auth login
    echo "   Google Drive authenticated!"
else
    echo "   Warning: gdcli not found. Skipping."
fi

echo ""

# Gmail
echo "2. Authenticating Gmail..."
read -p "   Press Enter to continue..."
if command -v gmcli &> /dev/null; then
    gmcli auth login
    echo "   Gmail authenticated!"
else
    echo "   Warning: gmcli not found. Skipping."
fi

echo ""

# OneDrive
echo "3. Authenticating OneDrive..."
read -p "   Press Enter to continue..."
if command -v onedrive &> /dev/null; then
    onedrive login
    echo "   OneDrive authenticated!"
else
    echo "   Warning: onedrive-cli not found. Skipping."
fi

echo ""

# Brave Search API
echo "4. Setting up Brave Search API key..."
echo "   Get your API key from: https://brave.com/search/api/"
read -p "   Enter your Brave Search API key (or press Enter to skip): " BRAVE_KEY

if [ -n "$BRAVE_KEY" ]; then
    echo "export BRAVE_API_KEY=$BRAVE_KEY" >> /etc/environment
    export BRAVE_API_KEY=$BRAVE_KEY
    echo "   Brave Search API key saved!"
else
    echo "   Skipping Brave Search setup."
fi

echo ""

# Anthropic API Key (for Claude Code)
echo "5. Setting up Anthropic API key..."
echo "   This is required for Claude Code CLI."
read -p "   Enter your Anthropic API key (or press Enter to skip): " ANTHROPIC_KEY

if [ -n "$ANTHROPIC_KEY" ]; then
    echo "export ANTHROPIC_API_KEY=$ANTHROPIC_KEY" >> /etc/environment
    export ANTHROPIC_API_KEY=$ANTHROPIC_KEY
    echo "   Anthropic API key saved!"
else
    echo "   Skipping (you may have already set this)."
fi

echo ""
echo "=== OAuth setup complete! ==="
echo ""
echo "Restarting DeepAgent service..."
systemctl restart deepagent

echo ""
echo "Service status:"
systemctl status deepagent --no-pager

echo ""
echo "You can now use the API at http://localhost:8000"
echo "Or expose it: labctl expose port 8000 --https"
