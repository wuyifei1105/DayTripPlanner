"""小红书数据抓取器 - 基于 Spider_XHS API 爬虫（替代 Playwright 浏览器自动化）"""
import asyncio
import time
import re
from typing import List, Dict, Any
from loguru import logger
from config import settings
from spider_xhs.apis.xhs_pc_apis import XHS_Apis
from spider_xhs.xhs_utils.data_util import handle_note_info


class XiaohongshuScraper:
    """小红书笔记抓取器（API 爬虫版）"""
    
    def __init__(self):
        self.platform = "xiaohongshu"
        self.xhs_apis = XHS_Apis()
    
    @property
    def cookies_str(self) -> str:
        """获取 cookie 字符串"""
        cookie = settings.xhs_cookies
        if not cookie:
            raise Exception("请在 .env 文件中配置 XHS_COOKIES（从浏览器 F12 获取小红书登录 cookie）")
        return cookie
    
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
        logger.info(f"🔍 Spider_XHS 搜索: {keyword}, 最多 {max_results} 条")
        
        # 1. 搜索笔记列表（同步调用放到线程池中避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        success, msg, notes = await loop.run_in_executor(
            None,
            lambda: self.xhs_apis.search_some_note(
                query=keyword,
                require_num=max_results,
                cookies_str=self.cookies_str,
                sort_type_choice=0,  # 综合排序
                note_type=2,  # 仅图文笔记（旅行攻略通常是图文）
            )
        )
        
        if not success:
            logger.error(f"搜索失败: {msg}")
            raise Exception(f"小红书搜索失败: {msg}")
        
        # 过滤出笔记类型的结果
        notes = [n for n in notes if n.get('model_type') == 'note']
        logger.info(f"📋 搜索到 {len(notes)} 篇笔记")
        
        # 2. 获取每个笔记的详细信息
        results = []
        for note in notes[:max_results]:
            try:
                note_id = note.get('id', '')
                xsec_token = note.get('xsec_token', '')
                note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search"
                
                # 获取笔记详情
                detail_success, detail_msg, detail_json = await loop.run_in_executor(
                    None,
                    lambda url=note_url: self.xhs_apis.get_note_info(url, self.cookies_str)
                )
                
                if detail_success and detail_json:
                    note_data = detail_json['data']['items'][0]
                    note_data['url'] = note_url
                    note_info = handle_note_info(note_data)
                    
                    # 转换为 DayTripPlanner 格式
                    result = self._convert_to_place_info(note_info)
                    if result:
                        results.append(result)
                        logger.info(f"  ✅ {result['title'][:30]}...")
                else:
                    logger.warning(f"  ❌ 获取笔记详情失败: {detail_msg}")
                
                # 避免请求过快
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"  ❌ 处理笔记失败: {e}")
                continue
        
        logger.info(f"📍 共获取 {len(results)} 条有效结果")
        return results
    
    def _convert_to_place_info(self, note_info: dict) -> Dict[str, Any]:
        """将爬虫获取的笔记信息转换为 DayTripPlanner 的地点格式
        
        Args:
            note_info: handle_note_info 处理后的笔记信息
        
        Returns:
            格式化的地点信息字典
        """
        title = note_info.get('title', '')
        desc = note_info.get('desc', '')
        
        if not title:
            return None
        
        # 从标题提取地点名称
        place_name = self._extract_place_name(title)
        
        # 猜测类别
        category = self._guess_category(title + " " + desc)
        
        # 解析互动数据
        likes = self._safe_int(note_info.get('liked_count', 0))
        collected = self._safe_int(note_info.get('collected_count', 0))
        comments = self._safe_int(note_info.get('comment_count', 0))
        
        return {
            "name": place_name,
            "title": title,
            "description": desc[:500] if desc else "",
            "likes": likes,
            "collected": collected,
            "comments": comments,
            "note_url": note_info.get('note_url', ''),
            "category": category,
            "source": "xiaohongshu",
            "tags": note_info.get('tags', []),
            "images": note_info.get('image_list', [])[:3],  # 最多保留3张图
            "author": note_info.get('nickname', ''),
            "upload_time": note_info.get('upload_time', ''),
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
