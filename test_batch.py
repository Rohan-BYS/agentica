import asyncio
from src.core.router import AIBrowserRouter

async def main():
    browser = AIBrowserRouter()
    
    print("--- Testing Batch Text Mode with Memory Limits ---")
    urls_to_test = [
        "https://example.com" for _ in range(20)
    ]
    
    results = await browser.browse_batch(urls_to_test, max_concurrency=10)
    
    success_count = sum(1 for r in results if r is not None and "content" in r)
    print(f"\nBatch complete! Successfully fetched {success_count} out of {len(urls_to_test)} pages.")
    
    if success_count > 0:
        print("\nSnippet of first result:")
        print(results[0]["content"][:300])

    await browser.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
