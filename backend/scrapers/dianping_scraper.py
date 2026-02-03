"""大众点评数据抓取器"""
import asyncio
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from playwright.async_api import Page
from .browser_manager import browser_manager


class DianpingScraper:
    """大众点评数据抓取器"""
    
    def __init__(self):
        self.platform = "dianping"
        self.base_url = "https://www.dianping.com"
    
    async def ensure_login(self) -> bool:
        """确保已登录"""
        is_logged_in = await browser_manager.check_login_status(self.platform)
        if not is_logged_in:
            return await browser_manager.prompt_login(self.platform)
        return True
    
    async def search(self, keyword: str, city: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索商家
        
        Args:
            keyword: 搜索关键词
            city: 城市名称
            max_results: 最大返回结果数
        
        Raises:
            Exception: 如果搜索失败
        """
        if not await self.ensure_login():
            raise Exception("请先登录大众点评后再试")
        
        page = await browser_manager.get_page(self.platform, headless=True)
        
        # 访问搜索页面 - 对关键词进行 URL 编码
        encoded_keyword = quote(keyword)
        # 大众点评搜索 URL 格式
        search_url = f"{self.base_url}/search/keyword/{ord(city[0]) if city else 1}/0_{encoded_keyword}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 提取商家信息
        shops = await self._extract_shops(page, max_results)
        return shops
    
    async def get_shop_detail(self, shop_name: str, city: str) -> Optional[Dict[str, Any]]:
        """获取单个商家详情
        
        用于补充小红书获取的地点信息
        """
        try:
            results = await self.search(shop_name, city, max_results=1)
            return results[0] if results else None
        except Exception as e:
            print(f"获取商家详情失败: {e}")
            return None
    
    async def _extract_shops(self, page: Page, max_results: int) -> List[Dict[str, Any]]:
        """从搜索结果页提取商家信息"""
        results = []
        
        # 等待商家列表加载
        await page.wait_for_selector(".shop-list, #shop-all-list", timeout=10000)
        
        shop_items = await page.query_selector_all(".shop-list li, .shop-item")
        
        for item in shop_items[:max_results]:
            try:
                # 商家名称
                name_el = await item.query_selector(".tit, h4, .shop-name")
                name = await name_el.inner_text() if name_el else ""
                name = name.strip()
                
                # 评分
                star_el = await item.query_selector(".sml-rank-stars, .star, .rating")
                rating = 0.0
                if star_el:
                    # 尝试从class或style中提取评分
                    class_name = await star_el.get_attribute("class") or ""
                    rating_match = re.search(r"star(\d+)", class_name)
                    if rating_match:
                        rating = int(rating_match.group(1)) / 10
                    else:
                        rating_text = await star_el.inner_text()
                        try:
                            rating = float(rating_text)
                        except:
                            pass
                
                # 人均消费
                price_el = await item.query_selector(".mean-price, .price, .avg-price")
                price = await price_el.inner_text() if price_el else ""
                price = re.sub(r"[人均:：]", "", price).strip()
                
                # 地址
                addr_el = await item.query_selector(".addr, .address, .tag-addr")
                address = await addr_el.inner_text() if addr_el else ""
                
                # 类别
                tag_el = await item.query_selector(".tag, .category")
                category = await tag_el.inner_text() if tag_el else ""
                
                # 评价数
                review_el = await item.query_selector(".review-num, .comment-num")
                review_count = 0
                if review_el:
                    review_text = await review_el.inner_text()
                    review_match = re.search(r"(\d+)", review_text)
                    if review_match:
                        review_count = int(review_match.group(1))
                
                if name:
                    results.append({
                        "name": name,
                        "rating": rating,
                        "price_range": price,
                        "address": address,
                        "category": self._normalize_category(category),
                        "review_count": review_count,
                        "source": "dianping",
                    })
                    
            except Exception as e:
                print(f"提取商家信息失败: {e}")
                continue
        
        return results
    
    def _normalize_category(self, category: str) -> str:
        """标准化类别"""
        category = category.lower()
        if any(kw in category for kw in ["餐", "美食", "饭", "菜", "火锅", "面"]):
            return "美食"
        elif any(kw in category for kw in ["景", "玩", "公园", "馆"]):
            return "景点"
        elif any(kw in category for kw in ["商", "购", "超市"]):
            return "购物"
        return "其他"


# 全局实例
dianping_scraper = DianpingScraper()
