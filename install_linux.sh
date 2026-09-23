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

# Ensure python3, pip, and venv are installed across any Linux distro
echo "[*] Detecting Linux distribution and installing dependencies..."
if command -v apt-get &>/dev/null; then
    # Debian, Ubuntu, Mint, Pop!_OS, Kali, etc.
    echo "[*] Detected Debian/Ubuntu family (apt)..."
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git
elif command -v dnf &>/dev/null; then
    # Fedora, RHEL, CentOS Stream, Rocky, Alma
    echo "[*] Detected Fedora/RHEL family (dnf)..."
    sudo dnf install -y python3 python3-pip git
elif command -v pacman &>/dev/null; then
    # Arch Linux, Manjaro, EndeavourOS
    echo "[*] Detected Arch Linux family (pacman)..."
    sudo pacman -Sy --noconfirm python python-pip git
elif command -v zypper &>/dev/null; then
    # openSUSE, SUSE
    echo "[*] Detected openSUSE family (zypper)..."
    sudo zypper install -y python3 python3-pip git
elif command -v apk &>/dev/null; then
    # Alpine Linux
    echo "[*] Detected Alpine Linux (apk)..."
    sudo apk add --no-cache python3 py3-pip git
else
    echo "[!] Unrecognized package manager. Ensure python3, python3-pip, and python3-venv are installed manually."
fi

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

# Make helper scripts executable
chmod +x run_mcp_stdio.sh launch_human.sh create_desktop_shortcut.sh 2>/dev/null || true
chmod +x run_mcp_http.sh 2>/dev/null || true

# Create desktop shortcut with logo for Human mode
echo "[*] Creating Desktop shortcut and Application Menu entry with Agentica logo..."
./create_desktop_shortcut.sh 2>/dev/null || true

echo ""
echo "================================================================="
echo "   [SUCCESS] Agentica is installed and ready on your system!     "
echo "================================================================="
echo ""
echo "👤 For Humans (Regular Desktop Browser with Co-Browsing on port 9222):"
echo "   - Click the 'Agentica' icon on your Desktop or in your App Menu"
echo "   - Or run: ./launch_human.sh"
echo ""
echo "🤖 For AI Agents (Hermes via MCP stdio):"
echo "   - Set command to: $PWD/run_mcp_stdio.sh"
echo ""
echo "🌐 For Remote MCP (HTTP / SSE server):"
echo "   - Run: ./run_mcp_http.sh"
echo ""
