#!/usr/bin/env bash
# ==============================================================================
# Agentica Browser - Universal Linux Installer
# Supports: Debian 12/13, Ubuntu, Fedora, RHEL, CentOS, Arch, openSUSE, Alpine
# ==============================================================================
set -e

echo "================================================================="
echo "       AGENTICA BROWSER: UNIVERSAL LINUX INSTALLER               "
echo "================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Fix ownership if cloned with sudo
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" "$SCRIPT_DIR" 2>/dev/null || true
fi

# Detect sudo requirement
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    else
        echo "[!] Warning: Not running as root and 'sudo' is not installed."
    fi
fi

# Ensure python3, pip, and venv are installed across any Linux distro
echo "[*] Detecting Linux distribution and installing system dependencies..."
if command -v apt-get &>/dev/null; then
    # Debian, Ubuntu, Mint, Pop!_OS, Kali, etc.
    echo "[*] Detected Debian/Ubuntu family (apt)..."
    $SUDO apt-get update -y
    $SUDO apt-get install -y python3 python3-pip python3-venv git curl
elif command -v dnf &>/dev/null; then
    # Fedora, RHEL, CentOS Stream, Rocky, Alma
    echo "[*] Detected Fedora/RHEL family (dnf)..."
    $SUDO dnf install -y python3 python3-pip git curl
elif command -v pacman &>/dev/null; then
    # Arch Linux, Manjaro, EndeavourOS
    echo "[*] Detected Arch Linux family (pacman)..."
    $SUDO pacman -Sy --noconfirm python python-pip git curl
elif command -v zypper &>/dev/null; then
    # openSUSE, SUSE
    echo "[*] Detected openSUSE family (zypper)..."
    $SUDO zypper install -y python3 python3-pip git curl
elif command -v apk &>/dev/null; then
    # Alpine Linux
    echo "[*] Detected Alpine Linux (apk)..."
    $SUDO apk add --no-cache python3 py3-pip git curl bash
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

# Install Playwright Chromium with system dependencies for Linux
echo "[*] Installing Playwright Chromium and OS library dependencies..."
playwright install --with-deps chromium

# Create data directories
mkdir -p data/hibernate data/screenshots data/sessions data/profiles/human

# Make helper scripts executable
chmod +x run_mcp_stdio.sh run_mcp_http.sh launch_human.sh create_desktop_shortcut.sh setup_systemd_service.sh 2>/dev/null || true

# Create desktop shortcut with logo for Human mode if desktop environment is present
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ] || [ -d "$HOME/Desktop" ]; then
    echo "[*] Creating Desktop shortcut and Application Menu entry with Agentica logo..."
    ./create_desktop_shortcut.sh 2>/dev/null || true
fi

echo ""
echo "================================================================="
echo "   [SUCCESS] Agentica is installed and ready on your system!     "
echo "================================================================="
echo ""
echo "👤 For Humans (Regular Desktop Browser with Co-Browsing on port 9222):"
echo "   - Click 'Agentica' in your Applications menu / Desktop"
echo "   - Or run: ./launch_human.sh"
echo ""
echo "🤖 For Local AI Agents (Hermes via MCP stdio):"
echo "   - Command: $PWD/run_mcp_stdio.sh"
echo "   - Or direct python: $PWD/venv/bin/python3 -u $PWD/src/server/mcp_server.py"
echo ""
echo "⚙️ For Local AI Agents (Hermes via Systemd Background Service):"
echo "   - Run: ./setup_systemd_service.sh"
echo "   - Connects to: http://127.0.0.1:8000/mcp (zero latency, starts on boot)"
echo ""
echo "🌐 For Remote / Ad-hoc MCP (HTTP / SSE server):"
echo "   - Run: ./run_mcp_http.sh"
echo "================================================================="
