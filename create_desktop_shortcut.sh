#!/usr/bin/env bash
# ==============================================================================
# Agentica - Linux Desktop Shortcut & Icon Creator
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$TARGET_USER")

DESKTOP_DIR="$USER_HOME/Desktop"
APPS_DIR="$USER_HOME/.local/share/applications"

mkdir -p "$APPS_DIR"

# Ensure launch_human.sh is executable
chmod +x "$SCRIPT_DIR/launch_human.sh"

DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=Agentica
GenericName=Web Browser
Comment=Dual-Mode AI-First Web Browser
Exec=$SCRIPT_DIR/launch_human.sh
Icon=$SCRIPT_DIR/agentica.png
Terminal=false
Categories=Network;WebBrowser;
StartupWMClass=agentica
"

# 1. Install to Applications Menu (Search / App Grid)
echo "$DESKTOP_CONTENT" > "$APPS_DIR/agentica.desktop"
chmod +x "$APPS_DIR/agentica.desktop"

# 2. Install to Desktop if Desktop folder exists
if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_CONTENT" > "$DESKTOP_DIR/agentica.desktop"
    chmod +x "$DESKTOP_DIR/agentica.desktop"
    # Allow launching on GNOME (Debian 13 default)
    if command -v gio &>/dev/null; then
        gio set "$DESKTOP_DIR/agentica.desktop" metadata::trusted true 2>/dev/null || true
    fi
fi

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo "[*] Success! Agentica is now available in your Application Menu and on your Desktop with its custom logo."
