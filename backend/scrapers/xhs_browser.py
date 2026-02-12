
import asyncio
import random
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger
from config import settings

class XhsBrowserScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def init_browser(self):
        """Initialize browser with stealth settings (supports local profile)"""
        if not self.playwright:
            logger.info("Starting Playwright browser...")
            self.playwright = await async_playwright().start()
            
            # Common args for stealth
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
            
            if settings.chrome_user_data_dir:
                logger.info(f"Using local Chrome profile: {settings.chrome_user_data_dir}")
                try:
                    # Launch persistent context with explicit profile and crash recovery suppression
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=settings.chrome_user_data_dir,
                        executable_path=settings.chrome_executable_path if settings.chrome_executable_path else None,
                        headless=False,
                        viewport={"width": 1280, "height": 800},
                        args=[
                            "--profile-directory=Default",
                            "--disable-session-crashed-bubble",
                            "--disable-infobars",
                            "--no-first-run",
                            "--no-default-browser-check",
                            "--disable-blink-features=AutomationControlled"
                        ],
                        ignore_default_args=["--enable-automation"],
                        timeout=30000 
                    )
                    logger.info("Persistent context launched successfully.")
                except Exception as e:
                    logger.error(f"Failed to launch persistent context: {e}")
                    raise e
                
                # Get existing page or create new one
                if self.context.pages:
                    self.page = self.context.pages[0]
                else:
                    self.page = await self.context.new_page()
            else:
                # Launch standard isolated browser
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=browser_args
                )
                
                self.context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai"
                )
                self.page = await self.context.new_page()
            
            # Inject stealth scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

    async def close(self):
        """Close browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def search(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for notes using browser automation"""
        try:
            if not self.page:
                await self.init_browser()
            
            logger.info(f"Adding cookies...")
            # Add cookies if available in settings AND not using local profile
            if settings.xhs_cookies and not settings.chrome_user_data_dir:
                await self._add_cookies(settings.xhs_cookies)
            elif settings.chrome_user_data_dir:
                logger.info("Using local profile, skipping manual cookie injection.")

            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
            logger.info(f"Navigating to: {search_url}")
            
            await self.page.goto(search_url, wait_until="domcontentloaded")
            
            # Wait for results
            try:
                # Wait for either feed-container or end-container or specific note items
                await self.page.wait_for_selector("section.note-item", timeout=10000)
            except Exception as e:
                logger.warning(f"Timeout waiting for results: {e}")
                # Save screenshot for debugging
                await self.page.screenshot(path="debug_search_fail.png")
                return []

            # Scroll to load more items if needed
            current_count = 0
            while current_count < max_results:
                items = await self.page.query_selector_all("section.note-item")
                current_count = len(items)
                if current_count >= max_results:
                    break
                
                # Scroll down
                await self.page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Check if we reached bottom? (Simple check for now)
                # If existing items count doesn't change after scroll, maybe break?
            
            # Extract data
            results = []
            items = await self.page.query_selector_all("section.note-item")
            
            for item in items[:max_results]:
                try:
                    # Extract basic info from the card
                    # Note: Selectors might need adjustment based on XHS updates
                    
                    # Title (usually in footer)
                    title_el = await item.query_selector(".footer .title span")
                    title = await title_el.inner_text() if title_el else ""
                    
                    # Author
                    author_el = await item.query_selector(".footer .author-wrapper .name")
                    author = await author_el.inner_text() if author_el else "Unknown"
                    
                    # Likes
                    like_el = await item.query_selector(".footer .like-wrapper .count")
                    likes = await like_el.inner_text() if like_el else "0"
                    
                    # Image (background image of the cover)
                    # Often it's a style attribute or an img tag
                    img_el = await item.query_selector(".cover")
                    # This might be tricky, usually style="background-image: url(...)"
                    # Or img tag inside
                    
                    # Link
                    # The item itself is usually an anchor or contains one
                    link_el = await item.query_selector("a.cover") 
                    if not link_el:
                         # Try finding any anchor
                         link_el = await item.query_selector("a")
                         
                    href = await link_el.get_attribute("href") if link_el else ""
                    note_url = f"https://www.xiaohongshu.com{href}" if href and not href.startswith("http") else href
                    
                    results.append({
                        "title": title,
                        "author": author,
                        "likes": likes,
                        "note_url": note_url,
                        "source": "xiaohongshu_browser"
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to parse item: {e}")
                    continue
            
            logger.info(f"Found {len(results)} items via browser")
            return results
            
        except Exception as e:
            logger.error(f"Browser search failed: {e}")
            await self.page.screenshot(path="error_browser_search.png")
            return []
        finally:
            # Note: In a persistent server, we might want to keep browser open?
            # For now, close it to release resources
            await self.close()

    async def _add_cookies(self, cookie_str: str):
        """Parse cookie string and add to context"""
        cookies = []
        try:
            # Handle standard cookie string format "key=value; key2=value2"
            for part in cookie_str.split(';'):
                part = part.strip()
                if not part:
                    continue
                if '=' in part:
                    name, value = part.split('=', 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".xiaohongshu.com",
                        "path": "/"
                    })
            
            if cookies:
                logger.info(f"Injecting {len(cookies)} cookies: {[c['name'] for c in cookies[:3]]}...")
                await self.context.add_cookies(cookies)
                
                # Check if they were actually set
                current_cookies = await self.context.cookies()
                logger.info(f"Browser now has {len(current_cookies)} cookies.")
            else:
                logger.warning("No valid cookies found in cookie string!")
        except Exception as e:
            logger.error(f"Failed to add cookies: {e}")

# Global instance
xhs_browser_scraper = XhsBrowserScraper()
