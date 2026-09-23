import asyncio
import json
from src.core.router import AIBrowserRouter

async def test_nexus_browser():
    print("=== Nexus AI Agent Browser Integration Test ===")
    router = AIBrowserRouter()
    
    try:
        # 1. Test Memory Status
        print("\n--- 1. Memory Status ---")
        mem = await router.get_memory_status()
        print(f"RAM Usage: {mem['ram_percent']}%")
        print(f"Safe Concurrency: {mem['allowed_concurrency']}")

        # 2. Test Tier 1 (Text)
        print("\n--- 2. Tier 1 Text Extraction ---")
        url = "https://example.com"
        res1 = await router.browse(url, mode="text")
        print(f"Mode Used: {res1['mode_used']}")
        print(f"Content snippet (first 100 chars):\n{res1['content'][:100]}...")

        # 3. Test Tier 2 (Structural)
        print("\n--- 3. Tier 2 Structural AXTree ---")
        res2 = await router.browse(url, mode="struct")
        print(f"Mode Used: {res2['mode_used']}")
        print(f"AXTree snippet:\n{res2['content'][:200]}...")

        # 4. Test Tier 3 (Visual Screenshot)
        print("\n--- 4. Tier 3 Visual Screenshot ---")
        res3 = await router.screenshot(url, headless=True)
        if "error" in res3:
            print(f"Screenshot error: {res3['error']}")
        else:
            base64_len = len(res3.get('base64', ''))
            print(f"Screenshot taken: {base64_len} bytes of base64 data")

        print("\n✅ All core systems operational.")

    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down engines...")
        await router.shutdown()

if __name__ == "__main__":
    asyncio.run(test_nexus_browser())
