"""小红书数据抓取器"""
import asyncio
import re
from typing import List, Dict, Any
from urllib.parse import quote
from playwright.async_api import Page
from .browser_manager import browser_manager


class XiaohongshuScraper:
    """小红书笔记抓取器"""
    
    def __init__(self):
        self.platform = "xiaohongshu"
        self.base_url = "https://www.xiaohongshu.com"
    
    async def ensure_login(self) -> bool:
        """确保已登录"""
        is_logged_in = await browser_manager.check_login_status(self.platform)
        if not is_logged_in:
            return await browser_manager.prompt_login(self.platform)
        return True
    
    async def search(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索笔记并提取地点信息
        
        Args:
            keyword: 搜索关键词，如"杭州西湖一日游"
            max_results: 最大返回结果数
        
        Returns:
            地点信息列表
        
        Raises:
            Exception: 如果搜索失败
        """
        # 确保已登录
        if not await self.ensure_login():
            raise Exception("请先登录小红书后再试")
        
        page = await browser_manager.get_page(self.platform, headless=True)
        
        # 访问搜索页面 - 对关键词进行 URL 编码
        encoded_keyword = quote(keyword)
        search_url = f"{self.base_url}/search_result?keyword={encoded_keyword}&source=web_search_result_notes"
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 等待笔记卡片加载
        await page.wait_for_selector(".note-item, .search-result-item", timeout=10000)
        
        # 滚动加载更多
        for _ in range(2):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
        
        # 提取笔记信息
        notes = await self._extract_notes(page, max_results)
        return notes
    
    async def _extract_notes(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """从页面提取笔记信息"""
        results = []
        
        # 尝试多种选择器
        note_cards = await page.query_selector_all("section.note-item, div[data-note-id]")
        
        for i, card in enumerate(note_cards[:max_results]):
            try:
                # 提取标题
                title_el = await card.query_selector(".title, h3, .note-title")
                title = await title_el.inner_text() if title_el else ""
                
                # 提取描述/摘要
                desc_el = await card.query_selector(".desc, .note-desc, p")
                desc = await desc_el.inner_text() if desc_el else ""
                
                # 提取点赞数
                like_el = await card.query_selector(".like-count, .count, span[class*='like']")
                likes_text = await like_el.inner_text() if like_el else "0"
                likes = self._parse_count(likes_text)
                
                # 提取链接
                link_el = await card.query_selector("a")
                href = await link_el.get_attribute("href") if link_el else ""
                note_url = f"{self.base_url}{href}" if href and not href.startswith("http") else href
                
                # 判断类别
                category = self._guess_category(title + " " + desc)
                
                if title:
                    results.append({
                        "name": self._extract_place_name(title),
                        "title": title,
                        "description": desc[:200] if desc else "",
                        "likes": likes,
                        "note_url": note_url,
                        "category": category,
                        "source": "xiaohongshu",
                    })
                    
            except Exception as e:
                print(f"提取笔记信息失败: {e}")
                continue
        
        return results
    
    def _parse_count(self, text: str) -> int:
        """解析数量文本（如 1.2万 -> 12000）"""
        text = text.strip()
        if not text:
            return 0
        
        try:
            if "万" in text:
                num = float(text.replace("万", ""))
                return int(num * 10000)
            elif "k" in text.lower():
                num = float(text.lower().replace("k", ""))
                return int(num * 1000)
            else:
                return int(re.sub(r"[^\d]", "", text) or 0)
        except:
            return 0
    
    def _guess_category(self, text: str) -> str:
        """根据文本猜测类别"""
        food_keywords = ["美食", "餐厅", "好吃", "吃饭", "火锅", "咖啡", "甜品", "小吃", "面馆", "饭店"]
        attraction_keywords = ["景点", "打卡", "拍照", "风景", "公园", "古镇", "博物馆", "寺庙", "湖", "山"]
        shopping_keywords = ["购物", "商场", "市集", "买", "特产"]
        
        for kw in food_keywords:
            if kw in text:
                return "美食"
        for kw in attraction_keywords:
            if kw in text:
                return "景点"
        for kw in shopping_keywords:
            if kw in text:
                return "购物"
        
        return "景点"  # 默认
    
    def _extract_place_name(self, title: str) -> str:
        """从标题提取地点名称"""
        # 简单处理：取|或｜前的部分
        for sep in ["|", "｜", "—", "-", "·"]:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        
        # 移除常见前缀
        prefixes = ["推荐", "必去", "探店", "打卡"]
        for prefix in prefixes:
            title = title.replace(prefix, "")
        
        return title.strip()[:30]  # 限制长度


# 全局实例
xiaohongshu_scraper = XiaohongshuScraper()
