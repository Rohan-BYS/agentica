import asyncio
import json
import time
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.async_api import async_playwright

async def get_all_sitemap_urls():
    base = "https://www.bys.marketing"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(f"{base}/sitemap.xml")
        soup = BeautifulSoup(r.text, "xml") if "xml" in r.text else BeautifulSoup(r.text, "html.parser")
        urls = [loc.text.strip() for loc in soup.find_all("loc")]
        return sorted(list(set(urls)))

async def crawl_page(context, url, sem):
    async with sem:
        page = await context.new_page()
        data = {
            "url": url,
            "status": "success",
            "title": "",
            "meta_desc": "",
            "canonical": "",
            "h1": [],
            "h2": [],
            "schema_types": [],
            "word_count": 0,
            "text_snippet": ""
        }
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            data["http_status"] = resp.status if resp else 0
            
            # Wait briefly for React hydration
            await page.wait_for_timeout(800)
            
            data["title"] = await page.title()
            
            # Extract meta tags
            meta_desc = await page.evaluate("() => document.querySelector('meta[name=\"description\"]')?.content || ''")
            canonical = await page.evaluate("() => document.querySelector('link[rel=\"canonical\"]')?.href || ''")
            data["meta_desc"] = meta_desc
            data["canonical"] = canonical
            
            # Headings
            h1s = await page.evaluate("() => Array.from(document.querySelectorAll('h1')).map(e => e.innerText.trim()).filter(Boolean)")
            h2s = await page.evaluate("() => Array.from(document.querySelectorAll('h2')).map(e => e.innerText.trim()).filter(Boolean)")
            data["h1"] = h1s
            data["h2"] = h2s
            
            # Schemas
            schemas = await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[type=\"application/ld+json\"]'));
                const types = [];
                for (const s of scripts) {
                    try {
                        const parsed = JSON.parse(s.innerText);
                        if (parsed['@type']) types.push(parsed['@type']);
                        if (parsed['@graph']) types.push(...parsed['@graph'].map(g => g['@type']));
                    } catch(e) {}
                }
                return types;
            }""")
            data["schema_types"] = schemas
            
            # Body text
            text = await page.evaluate("() => document.body.innerText || ''")
            words = text.split()
            data["word_count"] = len(words)
            data["text_snippet"] = text[:500].replace("\n", " ").strip()
            
        except Exception as e:
            data["status"] = "error"
            data["error_msg"] = str(e)
        finally:
            await page.close()
            return data

async def main():
    print("[*] Fetching all sitemap URLs...")
    urls = await get_all_sitemap_urls()
    print(f"[*] Discovered {len(urls)} total URLs.")
    
    start_time = time.time()
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Block images, fonts, styles, and media for maximum speed & lowest RAM
        context = await browser.new_context()
        await context.route("**/*.{png,jpg,jpeg,svg,webp,gif,woff,woff2,ttf,eot,css,mp4,webm}", lambda r: r.abort())
        
        # Concurrency limit of 8 pages at once
        sem = asyncio.Semaphore(8)
        tasks = [crawl_page(context, u, sem) for u in urls]
        
        # Progress reporting
        print(f"[*] Starting concurrent crawl of {len(urls)} pages (8 concurrent tabs)...")
        results = await asyncio.gather(*tasks)
        await browser.close()
        
    duration = time.time() - start_time
    print(f"[*] Crawl completed in {duration:.2f} seconds!")
    
    # Save full dataset
    with open("bys_exhaustive_dataset.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("[*] Saved complete dataset to bys_exhaustive_dataset.json")

if __name__ == "__main__":
    asyncio.run(main())
