import asyncio
import httpx
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        await page.goto("https://the-internet.herokuapp.com/login")
        await page.fill("#username", "tomsmith")
        await page.fill("#password", "SuperSecretPassword!")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        print("Tier 2 Logged in URL:", page.url)
        
        cookies = await ctx.cookies()
        rack_cookie = next(c for c in cookies if c["name"] == "rack.session")
        
        # Test HTTPX (Tier 1)
        client = httpx.AsyncClient(headers={"User-Agent": UA})
        client.cookies.set("rack.session", rack_cookie["value"], domain="the-internet.herokuapp.com", path="/")
        resp = await client.get("https://the-internet.herokuapp.com/secure", follow_redirects=False)
        print("Tier 1 HTTPX status:", resp.status_code)
        print("Tier 1 has Secure Area:", "Secure Area" in resp.text)
        await client.aclose()
        
        # Test Tier 3 (Screenshot context)
        ctx3 = await browser.new_context(user_agent=UA)
        await ctx3.add_cookies(cookies)
        page3 = await ctx3.new_page()
        await page3.goto("https://the-internet.herokuapp.com/secure")
        print("Tier 3 page URL:", page3.url)
        content3 = await page3.content()
        print("Tier 3 has Secure Area:", "Secure Area" in content3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
