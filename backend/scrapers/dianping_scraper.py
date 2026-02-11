"""大众点评数据抓取器 - 简化版（不依赖 Playwright）"""
import asyncio
import re
from typing import List, Dict, Any, Optional
from loguru import logger


class DianpingScraper:
    """大众点评数据抓取器（简化版）
    
    注意：当前版本不使用浏览器自动化，仅提供基础的数据补充功能。
    后续可接入大众点评 API 或其他数据源。
    """
    
    def __init__(self):
        self.platform = "dianping"
        self.base_url = "https://www.dianping.com"
    
    async def search(self, keyword: str, city: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索商家（当前为占位实现）"""
        logger.warning("大众点评搜索功能暂未实现（已移除 Playwright 依赖），返回空结果")
        return []
    
    async def get_shop_detail(self, shop_name: str, city: str) -> Optional[Dict[str, Any]]:
        """获取单个商家详情（当前为占位实现）"""
        logger.debug(f"大众点评查询: {shop_name} ({city}) - 功能暂未实现")
        return None
    
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
