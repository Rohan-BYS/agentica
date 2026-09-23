import asyncio
from src.core.router import AIBrowserRouter

async def test_login():
    router = AIBrowserRouter()
    print("1. Loading login page...")
    await router.browse("https://the-internet.herokuapp.com/login", mode="struct")
    
    print("2. Initial snapshot:")
    tree = await router.snapshot()
    print(tree)
    
    print("3. Filling credentials...")
    print(await router.fill("@e1", "tomsmith"))
    print(await router.fill("@e2", "SuperSecretPassword!"))
    
    print("4. Clicking submit button...")
    print(await router.click("@e3"))
    
    # Wait for navigation
    await asyncio.sleep(2)
    
    print("5. Current URL after submit:", router.tier2.page.url)
    post_tree = await router.snapshot()
    print("6. Post-login snapshot:")
    print(post_tree)
    
    await router.shutdown()

if __name__ == "__main__":
    asyncio.run(test_login())
