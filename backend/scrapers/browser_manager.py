"""Playwright浏览器会话管理器 - 支持登录一次，持久化session"""
import os
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import settings


class BrowserManager:
    """管理Playwright浏览器会话，支持session持久化"""
    
    def __init__(self, user_data_dir: str = None):
        self.user_data_dir = user_data_dir or settings.browser_data_dir
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._contexts: dict[str, BrowserContext] = {}
        self._login_status: dict[str, bool] = {}  # 缓存登录状态
        
        # 确保目录存在
        os.makedirs(self.user_data_dir, exist_ok=True)
    
    async def _ensure_playwright(self):
        """确保Playwright已启动"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
    
    async def _close_context(self, platform: str):
        """安全关闭指定平台的上下文"""
        if platform in self._contexts:
            try:
                await self._contexts[platform].close()
            except Exception:
                pass
            del self._contexts[platform]
    
    async def get_context(self, platform: str, headless: bool = True) -> BrowserContext:
        """获取指定平台的浏览器上下文（带持久化session）
        
        Args:
            platform: 平台名称，如 'xiaohongshu' 或 'dianping'
            headless: 是否无头模式（首次登录时应为False）
        """
        # 使用包含 headless 状态的 key，避免模式冲突
        context_key = f"{platform}_{'headless' if headless else 'visible'}"
        
        if context_key in self._contexts:
            return self._contexts[context_key]
        
        await self._ensure_playwright()
        
        # 使用persistent_context保存登录状态
        user_data_path = os.path.join(self.user_data_dir, platform)
        os.makedirs(user_data_path, exist_ok=True)
        
        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            headless=headless,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        
        self._contexts[context_key] = context
        return context
    
    async def get_page(self, platform: str, headless: bool = True) -> Page:
        """获取一个页面"""
        context = await self.get_context(platform, headless)
        pages = context.pages
        if pages:
            return pages[0]
        return await context.new_page()
    
    async def check_login_status(self, platform: str) -> bool:
        """检查指定平台是否已登录"""
        # 如果已缓存且已登录，直接返回
        if self._login_status.get(platform):
            return True
        
        try:
            page = await self.get_page(platform, headless=True)
            
            if platform == "xiaohongshu":
                await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
                await asyncio.sleep(2)
                # 检查是否有登录按钮（未登录状态）
                login_btn = await page.query_selector('text="登录"')
                is_logged = login_btn is None
                
            elif platform == "dianping":
                await page.goto("https://www.dianping.com", wait_until="domcontentloaded")
                await asyncio.sleep(2)
                login_btn = await page.query_selector('text="登录"')
                is_logged = login_btn is None
            else:
                is_logged = False
            
            # 缓存登录状态
            self._login_status[platform] = is_logged
            return is_logged
            
        except Exception as e:
            print(f"检查登录状态失败: {e}")
            return False
    
    async def prompt_login(self, platform: str, timeout: int = 120) -> bool:
        """提示用户登录（打开可见浏览器窗口，等待用户登录）
        
        使用轮询检测登录状态，不会阻塞事件循环
        
        Args:
            platform: 平台名称
            timeout: 等待超时时间（秒），默认120秒
        
        Returns:
            是否登录成功
        """
        print(f"\n{'='*50}")
        print(f"🔐 请在弹出的浏览器窗口中登录 {platform}")
        print(f"⏳ 等待登录中... (超时: {timeout}秒)")
        print(f"{'='*50}\n")
        
        # 使用非headless模式打开浏览器
        page = await self.get_page(platform, headless=False)
        
        if platform == "xiaohongshu":
            await page.goto("https://www.xiaohongshu.com")
        elif platform == "dianping":
            await page.goto("https://www.dianping.com")
        
        # 轮询等待登录完成
        start_time = asyncio.get_event_loop().time()
        check_interval = 3  # 每3秒检查一次
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                print(f"⚠️ 登录超时 ({timeout}秒)")
                return False
            
            # 检查登录状态
            try:
                if platform == "xiaohongshu":
                    login_btn = await page.query_selector('text="登录"')
                    if login_btn is None:
                        print(f"✅ {platform} 登录成功!")
                        self._login_status[platform] = True
                        return True
                elif platform == "dianping":
                    login_btn = await page.query_selector('text="登录"')
                    if login_btn is None:
                        print(f"✅ {platform} 登录成功!")
                        self._login_status[platform] = True
                        return True
            except Exception as e:
                print(f"检测登录状态时出错: {e}")
            
            # 等待一段时间再检查
            remaining = timeout - elapsed
            print(f"⏳ 等待登录... 剩余 {int(remaining)} 秒")
            await asyncio.sleep(check_interval)
    
    async def close(self):
        """关闭所有浏览器上下文"""
        for context in self._contexts.values():
            try:
                await context.close()
            except Exception:
                pass
        self._contexts.clear()
        self._login_status.clear()
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# 全局实例
browser_manager = BrowserManager()
