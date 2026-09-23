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
ICONS_DIR="$USER_HOME/.local/share/icons"
ICON_PATH="$SCRIPT_DIR/agentica.png"

mkdir -p "$APPS_DIR"
mkdir -p "$ICONS_DIR"

# Copy icon to user icon theme path
if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" "$ICONS_DIR/agentica.png"
    mkdir -p "$USER_HOME/.local/share/icons/hicolor/256x256/apps" 2>/dev/null || true
    cp "$ICON_PATH" "$USER_HOME/.local/share/icons/hicolor/256x256/apps/agentica.png" 2>/dev/null || true
fi

# Ensure launch_human.sh is executable
chmod +x "$SCRIPT_DIR/launch_human.sh"

DESKTOP_CONTENT="[Desktop Entry]
Version=1.0
Type=Application
Name=Agentica
GenericName=Web Browser
Comment=AI-First Dual-Mode Web Browser
Exec=$SCRIPT_DIR/launch_human.sh %U
Icon=$ICON_PATH
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
StartupWMClass=agentica
StartupNotify=true
"

# 1. Install to Applications Menu (Search / App Grid)
echo "$DESKTOP_CONTENT" > "$APPS_DIR/agentica.desktop"
chmod +x "$APPS_DIR/agentica.desktop"

# 2. Install to Desktop if Desktop folder exists
if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_CONTENT" > "$DESKTOP_DIR/agentica.desktop"
    chmod +x "$DESKTOP_DIR/agentica.desktop"
    # Mark as trusted for GNOME Desktop
    if command -v gio &>/dev/null; then
        gio set "$DESKTOP_DIR/agentica.desktop" metadata::trusted true 2>/dev/null || true
    fi
fi

# Update desktop and icon databases
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache "$ICONS_DIR" 2>/dev/null || true
fi

echo "[*] Success! Agentica is installed as a full desktop web browser."
echo "    - You can search for 'Agentica' in your Applications menu / Activities."
echo "    - You can launch it directly from the Desktop icon."
echo "    - Or run: ./launch_human.sh"
