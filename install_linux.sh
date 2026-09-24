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

# Target user detection
TARGET_USER="${SUDO_USER:-$USER}"

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

# Make all shell scripts executable
chmod +x *.sh 2>/dev/null || true

# Fix permissions so regular user owns everything
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo "[*] Setting file permissions for '$TARGET_USER'..."
    chown -R "$TARGET_USER":"$TARGET_USER" "$SCRIPT_DIR"
fi
chmod -R u+rwX "$SCRIPT_DIR/venv" "$SCRIPT_DIR/data" 2>/dev/null || true

# Setup Desktop shortcut if GUI desktop exists
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ] || [ -d "$HOME/Desktop" ]; then
    echo "[*] Creating Desktop shortcut and Application Menu entry with Agentica logo..."
    ./create_desktop_shortcut.sh 2>/dev/null || true
fi

# Automatically setup persistent systemd service if systemctl is available
if command -v systemctl &>/dev/null && [ -d /run/systemd/system ]; then
    echo "[*] Automatically configuring persistent systemd service for Hermes..."
    if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        su - "$TARGET_USER" -c "cd '$SCRIPT_DIR' && ./setup_systemd_service.sh" || true
    else
        ./setup_systemd_service.sh || true
    fi
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
echo "🤖 For Hermes AI Agent (Automatic Full Deployment):"
echo "   - Run: ./deploy_hermes.sh"
echo ""
echo "⚙️ Background Service (Persistent on boot, zero latency):"
echo "   - Status: systemctl --user status agentica"
echo "   - Local URL: http://127.0.0.1:8000/mcp"
echo "================================================================="
