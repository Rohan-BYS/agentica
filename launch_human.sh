#!/usr/bin/env bash
# ==============================================================================
# Agentica - Human Desktop Browser Launcher
# Launches the visible Chromium browser with persistent user profile and
# opens remote debugging port 9222 for AI co-browsing (Hermes).
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROFILE_DIR="$SCRIPT_DIR/data/profiles/human"
mkdir -p "$PROFILE_DIR"

# 1. Search for installed Playwright Chromium in ~/.cache
CHROME_BIN=""
for p in "$HOME/.cache/ms-playwright/chromium-"*/chrome-linux/chrome; do
    if [ -x "$p" ]; then
        CHROME_BIN="$p"
        break
    fi
done

# 2. Search local bin directory
if [ -z "$CHROME_BIN" ]; then
    for p in "$SCRIPT_DIR/bin/chromium-"*/chrome-linux/chrome "$SCRIPT_DIR/bin/chrome" "$SCRIPT_DIR/bin/chromium"; do
        if [ -x "$p" ]; then
            CHROME_BIN="$p"
            break
        fi
    done
fi

# 3. Search system installed Chromium or Chrome
if [ -z "$CHROME_BIN" ]; then
    for cmd in chromium-browser chromium google-chrome-stable google-chrome chrome; do
        if command -v "$cmd" &>/dev/null; then
            CHROME_BIN="$(command -v "$cmd")"
            break
        fi
    done
fi

# 4. Fallback: Query Playwright via python virtual environment
if [ -z "$CHROME_BIN" ] && [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    CHROME_BIN="$("$SCRIPT_DIR/venv/bin/python3" -c '
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print(p.chromium.executable_path)
except Exception:
    pass
' 2>/dev/null)"
fi

# 5. If still not found, try installing playwright chromium automatically
if [ -z "$CHROME_BIN" ] || [ ! -x "$CHROME_BIN" ]; then
    echo "[!] Chromium executable not found. Attempting to install via Playwright..."
    if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
        source "$SCRIPT_DIR/venv/bin/activate"
        playwright install chromium
        for p in "$HOME/.cache/ms-playwright/chromium-"*/chrome-linux/chrome; do
            if [ -x "$p" ]; then
                CHROME_BIN="$p"
                break
            fi
        done
    fi
fi

if [ -z "$CHROME_BIN" ] || [ ! -x "$CHROME_BIN" ]; then
    echo "[x] Error: Could not find or install Chromium browser."
    echo "    Please run: source venv/bin/activate && playwright install --with-deps chromium"
    exit 1
fi

echo "[*] Launching Agentica Browser (Human Mode)..."
echo "[*] Chrome Binary: $CHROME_BIN"
echo "[*] Profile Directory: $PROFILE_DIR"
echo "[*] AI Co-Browsing Port: 9222 (Hermes ready)"

# If no URLs provided, default to google.com or blank tab
EXTRA_ARGS=("$@")
if [ ${#EXTRA_ARGS[@]} -eq 0 ]; then
    EXTRA_ARGS=("https://www.google.com")
fi

exec "$CHROME_BIN" \
    --user-data-dir="$PROFILE_DIR" \
    --remote-debugging-port=9222 \
    --restore-last-session \
    --no-default-browser-check \
    --no-first-run \
    --start-maximized \
    --disable-session-crashed-bubble \
    --hide-crash-restore-bubble \
    --class=agentica \
    --name=agentica \
    "${EXTRA_ARGS[@]}"
