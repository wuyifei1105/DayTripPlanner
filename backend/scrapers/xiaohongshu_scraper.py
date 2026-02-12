
import asyncio
import random
from typing import List, Dict, Any
from loguru import logger
from config import settings
# from spider_xhs.apis.xhs_pc_apis import XHS_Apis # Deprecated API
# from spider_xhs.xhs_utils.data_util import handle_note_info
from scrapers.xhs_browser import xhs_browser_scraper

class XiaohongshuScraper:
    """小红书笔记抓取器（API 爬虫版 -> 浏览器自动化版）"""
    
    def __init__(self):
        self.platform = "xiaohongshu"
        # self.xhs_apis = XHS_Apis() # Deprecated
    
    async def search(self, keyword: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索笔记并提取地点信息 (使用 Playwright 浏览器)"""
        logger.info(f"🔍 XHS Browser 搜索: {keyword}, 最多 {max_results} 条")
        
        try:
            # 使用浏览器爬虫搜索
            browser_results = await xhs_browser_scraper.search(keyword, max_results)
            
            results = []
            for item in browser_results:
                # 转换格式
                converted = self._convert_to_place_info(item)
                if converted:
                    results.append(converted)
            
            logger.info(f"📍 共获取 {len(results)} 条有效结果")
            return results
            
        except Exception as e:
            logger.error(f"小红书搜索失败: {e}")
            return []

    def _convert_to_place_info(self, note_info: dict) -> Dict[str, Any]:
        """将爬虫获取的笔记信息转换为 DayTripPlanner 的地点格式"""
        title = note_info.get('title', '')
        # Browser scraper might not get full desc/content without clicking
        desc = note_info.get('desc', '') or title 
        
        if not title:
            return None
        
        # 从标题提取地点名称
        place_name = self._extract_place_name(title)
        
        # 猜测类别
        category = self._guess_category(title + " " + desc)
        
        # 解析互动数据
        likes = self._safe_int(note_info.get('likes', 0))
        
        return {
            "name": place_name,
            "title": title,
            "description": desc[:500],
            "likes": likes,
            "collected": 0, # Browser list view might not show this
            "comments": 0,  # Browser list view might not show this
            "note_url": note_info.get('note_url', ''),
            "category": category,
            "source": "xiaohongshu",
            "tags": [],
            "images": [], # To do: extract images in browser scraper
            "author": note_info.get('author', ''),
            "upload_time": "",
        }
    
    def _safe_int(self, value) -> int:
        """安全转换为整数"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return 0
            try:
                import re
                if "万" in text:
                    return int(float(text.replace("万", "")) * 10000)
                elif "k" in text.lower():
                    return int(float(text.lower().replace("k", "")) * 1000)
                else:
                    return int(re.sub(r"[^\d]", "", text) or 0)
            except:
                return 0
        return 0
    
    def _guess_category(self, text: str) -> str:
        """根据文本猜测类别"""
        food_keywords = ["美食", "餐厅", "好吃", "吃饭", "火锅", "咖啡", "甜品", "小吃", "面馆", "饭店", "烧烤", "奶茶"]
        attraction_keywords = ["景点", "打卡", "拍照", "风景", "公园", "古镇", "博物馆", "寺庙", "湖", "山", "古城", "夜景"]
        shopping_keywords = ["购物", "商场", "市集", "买", "特产", "步行街"]
        
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
