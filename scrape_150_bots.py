import asyncio
import time
import os
import psutil
import csv
from pathlib import Path
from src.core.router import AIBrowserRouter
from src.core.memory_manager import MemoryManager

# Top 150 Global Non-Adult Websites
TOP_150_DOMAINS = [
    "https://www.google.com", "https://www.youtube.com", "https://www.wikipedia.org",
    "https://www.amazon.com", "https://www.reddit.com", "https://www.yahoo.com",
    "https://www.duckduckgo.com", "https://www.bing.com", "https://www.linkedin.com",
    "https://www.microsoft.com", "https://www.apple.com", "https://www.github.com",
    "https://www.ebay.com", "https://www.cnn.com", "https://www.bbc.com",
    "https://www.nytimes.com", "https://www.weather.com", "https://www.imdb.com",
    "https://www.walmart.com", "https://www.quora.com", "https://www.pinterest.com",
    "https://www.stackoverflow.com", "https://www.twitch.tv", "https://www.espn.com",
    "https://www.fandom.com", "https://www.healthline.com", "https://www.tripadvisor.com",
    "https://www.spotify.com", "https://www.aliexpress.com", "https://www.forbes.com",
    "https://www.theguardian.com", "https://www.huffpost.com", "https://www.foxnews.com",
    "https://www.usatoday.com", "https://www.booking.com", "https://www.salesforce.com",
    "https://www.shopify.com", "https://www.cloudflare.com", "https://www.stripe.com",
    "https://www.canva.com", "https://www.adobe.com", "https://www.medium.com",
    "https://www.notion.so", "https://www.zoom.us", "https://www.dropbox.com",
    "https://www.craigslist.org", "https://www.target.com", "https://www.ietf.org",
    "https://www.w3.org", "https://www.archive.org", "https://www.wordpress.com", 
    "https://www.tumblr.com", "https://www.vimeo.com", "https://www.dailymotion.com", 
    "https://www.soundcloud.com", "https://www.bbc.co.uk", "https://www.msn.com", 
    "https://www.ikea.com", "https://www.samsung.com", "https://www.sony.com", 
    "https://www.cisco.com", "https://www.oracle.com", "https://www.intel.com", 
    "https://www.nvidia.com", "https://www.amd.com", "https://www.asus.com", 
    "https://www.dell.com", "https://www.hp.com", "https://www.lenovo.com", 
    "https://www.acer.com", "https://www.panasonic.com", "https://www.lg.com", 
    "https://www.nintendo.com", "https://www.playstation.com", "https://www.xbox.com", 
    "https://www.steampowered.com", "https://www.epicgames.com", "https://www.ea.com", 
    "https://www.ubisoft.com", "https://www.rockstargames.com", "https://www.blizzard.com", 
    "https://www.riotgames.com", "https://www.roblox.com", "https://www.minecraft.net", 
    "https://www.pokemon.com", "https://www.bandainamcoent.com", "https://www.square-enix.com", 
    "https://www.capcom.com", "https://www.sega.com", "https://www.konami.com", 
    "https://www.snk-corp.co.jp", "https://www.koeitecmo.co.jp", "https://www.nexon.com", 
    "https://www.ncsoft.com", "https://www.krafton.com", "https://www.pearlabyss.com", 
    "https://www.mihoyo.com", "https://www.cygames.co.jp", "https://www.colopl.co.jp", 
    "https://www.mixi.co.jp", "https://www.linecorp.com", "https://www.kakao.com", 
    "https://www.naver.com", "https://www.daum.net", "https://www.nate.com", 
    "https://www.tistory.com", "https://www.dcinside.com", "https://www.ruliweb.com", 
    "https://www.inven.co.kr", "https://www.fmkorea.com", "https://www.clien.net", 
    "https://www.ppomppu.co.kr", "https://www.bobaedream.co.kr", "https://www.slrclub.com", 
    "https://www.todayhumor.co.kr", "https://www.theqoo.net", "https://www.instiz.net", 
    "https://www.pann.nate.com", "https://www.ygosu.com", "https://www.etoland.co.kr", 
    "https://www.ilbe.com", "https://www.dogdrip.net", "https://www.mercadolibre.com", 
    "https://www.shopee.com", "https://www.lazada.com", "https://www.tokopedia.com", 
    "https://www.bukalapak.com", "https://www.flipkart.com", "https://www.myntra.com", 
    "https://www.snapdeal.com", "https://www.shopclues.com", "https://www.paytmmall.com", 
    "https://www.tatacliq.com", "https://www.ajio.com", "https://www.nykaa.com", 
    "https://www.zomato.com", "https://www.swiggy.com", "https://www.coursera.org",
    "https://www.udemy.com", "https://www.edx.org", "https://www.khanacademy.org",
    "https://www.codecademy.com", "https://www.udacity.com", "https://www.skillshare.com",
    "https://www.pluralsight.com", "https://www.lynda.com", "https://www.datacamp.com"
]

def get_process_ram_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

async def run_150_benchmark():
    # De-duplicate list just in case
    domains = list(set(TOP_150_DOMAINS))
    
    print("=================================================================")
    print("    NEXUS AI AGENT BROWSER: 150-WEBSITE MASS CONCURRENT SCRAPE   ")
    print("=================================================================\n")
    
    mem_mgr = MemoryManager()
    router = AIBrowserRouter()
    
    start_sys_ram = mem_mgr.get_usage_percent()
    start_proc_ram = get_process_ram_mb()
    
    print(f"[*] Total Target Domains: {len(domains)}")
    print(f"[*] Allowed Concurrency : {mem_mgr.get_allowed_concurrency()} simultaneous requests\n")
    print("--- STARTING SCRAPE IN BACKGROUND ---\n")
    
    start_time = time.time()
    
    # Run batch browse
    results = await router.browse_batch(domains, max_concurrency=30)
    
    total_time = time.time() - start_time
    
    success_count = 0
    csv_filename = "top_150_bot_info.csv"
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Status", "Content_Length", "Bot_Preview"])
        
        for i, res in enumerate(results, 1):
            url = res.get("url", "unknown")
            content = res.get("content", "")
            content_len = len(content)
            
            is_error = content.startswith("Error:") or "Client error" in content[:100]
            status = "FAIL" if is_error else "OK"
            if not is_error:
                success_count += 1
                
            snippet = content[:150].replace("\n", " ").strip()
            writer.writerow([url, status, content_len, snippet])
            
    print("\n=================================================================")
    print("                     SCRAPE RESULTS & STATS                      ")
    print("=================================================================")
    print(f"[*] Total Execution Time      : {total_time:.2f} seconds")
    print(f"[*] Successfully Scraped      : {success_count} / {len(domains)} websites")
    print(f"[*] Report saved to           : {csv_filename}")
    print("=================================================================\n")
    
    await router.shutdown()

if __name__ == "__main__":
    asyncio.run(run_150_benchmark())
