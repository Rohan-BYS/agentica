import asyncio
import json
import base64
from pathlib import Path
from src.core.router import AIBrowserRouter

async def simulate_agent_workflow():
    print("🤖 --- AI AGENT WORKFLOW SIMULATION --- 🤖\n")
    router = AIBrowserRouter()
    
    try:
        # Step 1: The AI wants to read documentation (Text mode is best)
        target_url = "https://developer.mozilla.org/en-US/docs/Web/HTML"
        print(f"[*] Agent Intent: Read documentation from {target_url}")
        print("[*] Action: router.browse(mode='text')")
        
        doc_result = await router.browse(target_url, mode="text")
        
        print(f"\n✅ Result (First 250 chars of Markdown):")
        print("-" * 40)
        print(doc_result['content'][:250] + "...\n")
        print("-" * 40)

        # Step 2: The AI wants to interact with a web app (Structural mode)
        app_url = "https://news.ycombinator.com/"
        print(f"\n[*] Agent Intent: Interact with Hacker News")
        print("[*] Action: router.browse(mode='struct')")
        
        ax_result = await router.browse(app_url, mode="struct")
        
        print(f"\n✅ Result (Accessibility Tree Snippet):")
        print("-" * 40)
        # Find the first few interactive elements with @eN tags
        lines = ax_result['content'].split('\n')
        interactive_lines = [l for l in lines if '[@e' in l][:5]
        for line in interactive_lines:
            print(line)
        print("-" * 40)

        # Step 3: The AI wants to visually verify a chart or layout
        print(f"\n[*] Agent Intent: Visually verify layout of example.com")
        print("[*] Action: router.screenshot()")
        
        screenshot_result = await router.screenshot("https://example.com", headless=True)
        if "image_base64" in screenshot_result:
            # Save the image to disk so the user can verify it!
            img_data = base64.b64decode(screenshot_result["image_base64"])
            out_path = Path("agent_vision_test.png")
            out_path.write_bytes(img_data)
            print(f"\n✅ Result: Captured screenshot successfully!")
            print(f"📸 Saved to: {out_path.absolute()}")
        else:
            print("❌ Failed to capture screenshot.")

    finally:
        print("\n[*] Agent workflow complete. Shutting down browser...")
        await router.shutdown()

if __name__ == "__main__":
    asyncio.run(simulate_agent_workflow())
