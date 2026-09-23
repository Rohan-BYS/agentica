import asyncio
import time
import os
import psutil
from pathlib import Path
from src.core.router import AIBrowserRouter
from src.core.memory_manager import MemoryManager

# Top 50 Clean, Global Non-Adult Websites
TOP_50_DOMAINS = [
    "https://www.google.com",
    "https://www.youtube.com",
    "https://www.wikipedia.org",
    "https://www.amazon.com",
    "https://www.reddit.com",
    "https://www.yahoo.com",
    "https://www.duckduckgo.com",
    "https://www.bing.com",
    "https://www.linkedin.com",
    "https://www.microsoft.com",
    "https://www.apple.com",
    "https://www.github.com",
    "https://www.ebay.com",
    "https://www.cnn.com",
    "https://www.bbc.com",
    "https://www.nytimes.com",
    "https://www.weather.com",
    "https://www.imdb.com",
    "https://www.walmart.com",
    "https://www.quora.com",
    "https://www.pinterest.com",
    "https://www.stackoverflow.com",
    "https://www.twitch.tv",
    "https://www.espn.com",
    "https://www.fandom.com",
    "https://www.healthline.com",
    "https://www.tripadvisor.com",
    "https://www.spotify.com",
    "https://www.aliexpress.com",
    "https://www.forbes.com",
    "https://www.theguardian.com",
    "https://www.huffpost.com",
    "https://www.foxnews.com",
    "https://www.usatoday.com",
    "https://www.booking.com",
    "https://www.salesforce.com",
    "https://www.shopify.com",
    "https://www.cloudflare.com",
    "https://www.stripe.com",
    "https://www.canva.com",
    "https://www.adobe.com",
    "https://www.medium.com",
    "https://www.notion.so",
    "https://www.zoom.us",
    "https://www.dropbox.com",
    "https://www.craigslist.org",
    "https://www.target.com",
    "https://www.ietf.org",
    "https://www.w3.org",
    "https://www.archive.org"
]

def get_process_ram_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

async def run_50_benchmark():
    print("=================================================================")
    print("    NEXUS AI AGENT BROWSER: 50-WEBSITE MASS CONCURRENT STRESS TEST")
    print("=================================================================\n")
    
    mem_mgr = MemoryManager()
    router = AIBrowserRouter()
    
    start_sys_ram = mem_mgr.get_usage_percent()
    start_proc_ram = get_process_ram_mb()
    
    print(f"[*] Baseline System RAM : {start_sys_ram:.1f}%")
    print(f"[*] Baseline Python Process RAM: {start_proc_ram:.1f} MB")
    print(f"[*] Total Target Domains: {len(TOP_50_DOMAINS)}")
    print(f"[*] Allowed Concurrency : {mem_mgr.get_allowed_concurrency()} simultaneous requests\n")
    print("--- STARTING HARVEST (Monitor Task Manager Now) ---\n")
    
    start_time = time.time()
    
    # Run batch browse with adaptive memory-safe concurrency
    results = await router.browse_batch(TOP_50_DOMAINS, max_concurrency=25)
    
    total_time = time.time() - start_time
    end_sys_ram = mem_mgr.get_usage_percent()
    end_proc_ram = get_process_ram_mb()
    
    print("\n=================================================================")
    print("                        HARVEST RESULTS                          ")
    print("=================================================================\n")
    
    success_count = 0
    total_extracted_chars = 0
    
    # Save a clean digest report of what the agent learned
    report_lines = ["# 50 Website Content Harvest Digest\n\n"]
    
    for i, res in enumerate(results, 1):
        url = res.get("url", "unknown")
        content = res.get("content", "")
        content_len = len(content)
        total_extracted_chars += content_len
        
        # Check success
        is_error = content.startswith("Error:") or "Client error" in content[:100]
        status = "FAIL" if is_error else "OK"
        if not is_error:
            success_count += 1
            
        snippet = content[:80].replace("\n", " ").strip()
        print(f"[{i:02d}/50] [{status}] {url[:30]:<30} | {content_len:>6} chars | {snippet[:40]}")
        
        report_lines.append(f"## {i}. {url}\n")
        report_lines.append(f"- **Status**: {status}\n")
        report_lines.append(f"- **Extracted Size**: {content_len} characters\n")
        report_lines.append(f"- **Preview**:\n```\n{content[:300]}\n```\n\n---\n")

    report_path = Path("harvest_50_report.md")
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    
    print("\n=================================================================")
    print("                     MEMORY & PERFORMANCE STATS                  ")
    print("=================================================================")
    print(f"[*] Total Execution Time      : {total_time:.2f} seconds")
    print(f"[*] Successfully Harvested    : {success_count} / {len(TOP_50_DOMAINS)} websites")
    print(f"[*] Total Text Data Extracted : {total_extracted_chars:,} characters (~{total_extracted_chars//4:,} tokens)")
    print(f"[*] Peak Process RAM Added    : +{end_proc_ram - start_proc_ram:.1f} MB")
    print(f"[*] Final Process RAM         : {end_proc_ram:.1f} MB")
    print(f"[*] System RAM Before / After : {start_sys_ram:.1f}% -> {end_sys_ram:.1f}%")
    print(f"[*] Report saved to           : {report_path.absolute()}")
    print("=================================================================\n")
    
    await router.shutdown()

if __name__ == "__main__":
    asyncio.run(run_50_benchmark())
