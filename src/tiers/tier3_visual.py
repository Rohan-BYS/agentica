import asyncio
import base64
import json
import io
import math
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

UNIFIED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

class Tier3VisualEngine:
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.playwright = None
        self.browser = None

    async def _init_browser(self, headless=True):
        if not self.playwright:
            self.playwright = await async_playwright().start()
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=headless)

    async def _get_page(self, url: str, headless: bool = True, cookies: Optional[list] = None):
        await self._init_browser(headless=headless)
        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            user_agent=UNIFIED_USER_AGENT
        )
        if cookies:
            try:
                await context.add_cookies(cookies)
            except Exception:
                pass
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        return context, page

    async def capture_screenshot(self, url: str, headless: bool = True, cookies: Optional[list] = None) -> dict:
        context, page = await self._get_page(url, headless, cookies=cookies)
        try:
            import os
            import time
            from pathlib import Path
            screenshot_bytes = await page.screenshot(full_page=True)
            b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Save to disk for agent media consumption (e.g. Telegram MEDIA:/path)
            screenshots_dir = Path("data/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            filename = f"screenshot_{int(time.time() * 1000)}.png"
            file_path = screenshots_dir / filename
            file_path.write_bytes(screenshot_bytes)
            
            return {
                "status": "success",
                "file_path": str(file_path.resolve()),
                "image_base64": b64,
                "url": url
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def capture_element(self, url: str, selector: str, headless: bool = True) -> dict:
        context, page = await self._get_page(url, headless)
        try:
            # We use CDP for DOM.getBoxModel
            client = await page.context.new_cdp_session(page)
            
            # evaluate to get objectId
            handle = await page.evaluate_handle(f"document.querySelector('{selector}')")
            if not handle:
                return {"status": "error", "message": f"Element {selector} not found"}
            
            # Need to get remote object id
            # Playwright handle doesn't expose objectId directly easily in CDP format,
            # so we'll just get the box model via page.evaluate
            
            box = await page.evaluate(f'''() => {{
                const el = document.querySelector('{selector}');
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {{x: rect.x, y: rect.y, width: rect.width, height: rect.height}};
            }}''')
            
            if not box:
                return {"status": "error", "message": "Could not get bounding box"}
            
            screenshot_bytes = await page.screenshot()
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            # Crop
            left = box['x']
            top = box['y']
            right = left + box['width']
            bottom = top + box['height']
            cropped = img.crop((left, top, right, bottom))
            
            buf = io.BytesIO()
            cropped.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            return {"status": "success", "image_base64": b64, "box": box}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def capture_annotated(self, url: str, headless: bool = True) -> dict:
        context, page = await self._get_page(url, headless)
        try:
            # Extract elements with their bounding boxes
            elements_data = await page.evaluate('''() => {
                const elements = Array.from(document.querySelectorAll('a, button, input, select, textarea'));
                return elements.map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    let tag = el.tagName.toLowerCase();
                    return {
                        index: index,
                        tag: tag,
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        visible: rect.width > 0 && rect.height > 0
                    };
                }).filter(e => e.visible);
            }''')

            screenshot_bytes = await page.screenshot(full_page=True)
            img = Image.open(io.BytesIO(screenshot_bytes)).convert("RGBA")
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except IOError:
                font = ImageFont.load_default()

            colors = {
                'button': '#FF6B6B',
                'input': '#4ECDC4',
                'select': '#45B7D1',
                'a': '#96CEB4',
                'textarea': '#FF8C42'
            }

            for el in elements_data:
                x, y, w, h = el['x'], el['y'], el['width'], el['height']
                color = colors.get(el['tag'], '#000000')
                
                # Draw bounding box
                draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                
                # Draw badge
                text = str(el['index'])
                
                # Smart badge placement
                # small elements (<60x30px) -> above, large -> centered
                if w < 60 or h < 30:
                    badge_x = x
                    badge_y = max(0, y - 20)
                else:
                    badge_x = x + w/2 - 10
                    badge_y = y + h/2 - 10
                    
                # Using textbbox to determine size if possible, else fixed approx
                try:
                    bbox = draw.textbbox((badge_x, badge_y), text, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                except AttributeError:
                    tw, th = 10, 10
                    
                draw.rectangle([badge_x, badge_y, badge_x + tw + 4, badge_y + th + 4], fill=color)
                draw.text((badge_x + 2, badge_y + 2), text, fill="white", font=font)

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return {"status": "success", "image_base64": b64, "elements_count": len(elements_data)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def extract_structured_data(self, url: str) -> dict:
        context, page = await self._get_page(url, True)
        try:
            data = await page.evaluate('''() => {
                const res = { jsonLd: [], openGraph: {}, twitter: {} };
                
                // JSON-LD
                document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                    try { res.jsonLd.push(JSON.parse(script.innerText)); } catch(e) {}
                });
                
                // OpenGraph & Twitter
                document.querySelectorAll('meta').forEach(meta => {
                    const property = meta.getAttribute('property');
                    const name = meta.getAttribute('name');
                    const content = meta.getAttribute('content');
                    
                    if (property && property.startsWith('og:')) {
                        res.openGraph[property.substring(3)] = content;
                    }
                    if (name && name.startsWith('twitter:')) {
                        res.twitter[name.substring(8)] = content;
                    }
                });
                return res;
            }''')
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def extract_by_schema(self, url: str, schema: dict) -> dict:
        context, page = await self._get_page(url, True)
        try:
            # We inject a JS function that tries to map the schema
            js_code = f'''(schema) => {{
                function extract(node, sch) {{
                    if (typeof sch === 'string') {{
                        const el = node.querySelector(sch);
                        return el ? el.innerText.trim() : null;
                    }}
                    if (Array.isArray(sch)) {{
                        const selector = sch[0];
                        const subSch = sch[1];
                        const els = Array.from(node.querySelectorAll(selector));
                        return els.map(el => extract(el, subSch));
                    }}
                    if (typeof sch === 'object') {{
                        const res = {{}};
                        for (const key in sch) {{
                            if (sch[key].selector && sch[key].attr) {{
                                const el = node.querySelector(sch[key].selector);
                                res[key] = el ? el.getAttribute(sch[key].attr) : null;
                                if (sch[key].attr === 'href' && res[key] && !res[key].startsWith('http')) {{
                                    res[key] = new URL(res[key], document.baseURI).href;
                                }}
                            }} else {{
                                res[key] = extract(node, sch[key]);
                            }}
                        }}
                        return res;
                    }}
                    return null;
                }}
                return extract(document, schema);
            }}'''
            data = await page.evaluate(js_code, schema)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def generate_pdf(self, url: str) -> dict:
        context, page = await self._get_page(url, True)
        try:
            client = await page.context.new_cdp_session(page)
            pdf_res = await client.send("Page.printToPDF")
            pdf_b64 = pdf_res.get("data")
            return {"status": "success", "pdf_base64": pdf_b64}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await context.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
