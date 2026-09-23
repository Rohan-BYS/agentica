import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

async def launch_human_profile():
    print("Launching Agentica Browser (Human Profile)...")
    
    # Path for persistent user data
    project_dir = Path(__file__).parent.parent.parent.absolute()
    user_data_dir = project_dir / "data" / "profiles" / "human"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure Playwright uses local binaries if present
    local_bin = project_dir / "bin"
    if local_bin.exists() and any(local_bin.glob("chromium*")):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(local_bin)
    
    async with async_playwright() as p:
        # Find custom branded agentica executable if on Windows, else use standard chromium
        executable_path = None
        try:
            original_exe = Path(p.chromium.executable_path)
            agentica_exe = original_exe.parent / "agentica.exe"
            if agentica_exe.exists():
                executable_path = str(agentica_exe)
        except Exception:
            pass
        
        # Launch Chromium with persistent context and remote debugging port 9222
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            executable_path=executable_path,
            headless=False,
            no_viewport=True,  # This tells the engine to let the OS window dictate the viewport
            args=[
                "--remote-debugging-port=9222",
                "--restore-last-session",
                "--no-default-browser-check",
                "--start-maximized",  # Start fully expanded
                "--disable-session-crashed-bubble",
                "--hide-crash-restore-bubble"
            ]
        )
        
        pages = browser_context.pages
        if len(pages) == 0:
            page = await browser_context.new_page()
            await page.goto("https://google.com")
        else:
            page = pages[0]
            
        print("Browser running. Press Ctrl+C to exit in console, or close the browser window.")
        
        # Wait indefinitely until the browser context is closed by the user
        try:
            while browser_context.pages:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            print("Browser closed.")

if __name__ == "__main__":
    try:
        asyncio.run(launch_human_profile())
    except KeyboardInterrupt:
        print("Exiting...")
