#!/usr/bin/env bash
# ==============================================================================
# Agentica Browser - Automated Installer for Debian 13 / Ubuntu / Linux
# ==============================================================================
set -e

echo "================================================================="
echo "       AGENTICA BROWSER: LINUX (DEBIAN 13 / UBUNTU) SETUP        "
echo "================================================================="

# Fix ownership if cloned with sudo
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" .
fi

# Ensure python3, pip, and venv are installed
echo "[*] Checking system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

# Create virtual environment if not present
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate venv
echo "[*] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python requirements
echo "[*] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Install Playwright Chromium with system dependencies for Debian 13
echo "[*] Installing Playwright Chromium and OS library dependencies..."
playwright install --with-deps chromium

# Create data directories
mkdir -p data/hibernate data/screenshots data/sessions

# Make helper launcher executable
chmod +x run_mcp_stdio.sh 2>/dev/null || true
chmod +x run_mcp_http.sh 2>/dev/null || true

echo ""
echo "================================================================="
echo "   [SUCCESS] Agentica is installed and ready on your system!     "
echo "================================================================="
echo ""
echo "To run standard MCP over stdio for local agents (Hermes):"
echo "  ./run_mcp_stdio.sh"
echo ""
echo "To run MCP HTTP / SSE server:"
echo "  ./run_mcp_http.sh"
echo ""
