"""基于LangGraph的多Agent工作流"""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import asyncio

from models.schemas import PlaceInfo, TripPlan, TripStop, PlaceCategory, DataSource
from services.llm_service import llm_service
from services.amap_service import amap_service
from scrapers.xiaohongshu_scraper import xiaohongshu_scraper
from scrapers.dianping_scraper import dianping_scraper


class TripPlannerState(TypedDict):
    """LangGraph状态定义"""
    # 输入
    location: str
    preferences: List[str]
    start_time: str
    
    # 共享数据池
    places: Annotated[List[dict], "收集到的所有地点"]
    
    # 处理状态
    current_step: str
    messages: Annotated[List[str], add_messages]
    error: Optional[str]
    
    # 输出
    plan: Optional[dict]


async def xiaohongshu_node(state: TripPlannerState) -> TripPlannerState:
    """小红书搜索节点 - 爬虫获取数据 + LLM 分析内容"""
    location = state["location"]
    messages = list(state.get("messages", []))
    places = list(state.get("places", []))
    
    messages.append(f"🔍 正在通过 XHS Browser 浏览器搜索: {location} 一日游推荐...")
    
    try:
        # 搜索景点和美食
        keywords = [
            f"{location}一日游",
            f"{location}美食推荐",
            f"{location}必去景点",
        ]
        
        all_notes = []
        for keyword in keywords:
            try:
                results = await xiaohongshu_scraper.search(keyword, max_results=5)
                all_notes.extend(results)
                messages.append(f"  ✅ 搜索'{keyword}'找到 {len(results)} 条结果")
            except Exception as e:
                messages.append(f"  ⚠️ 搜索'{keyword}'失败: {str(e)}")
        
        if all_notes:
            # 使用 LLM SubAgent 分析爬虫获取的笔记数据
            messages.append(f"🤖 LLM SubAgent 正在分析 {len(all_notes)} 条笔记内容...")
            analyzed_places = await llm_service.analyze_xhs_notes(all_notes, location)
            
            if analyzed_places:
                messages.append(f"  ✅ LLM 从笔记中提取了 {len(analyzed_places)} 个地点")
                
                # 合并爬虫数据和 LLM 分析结果
                for ap in analyzed_places:
                    place = {
                        "name": ap.get("name", ""),
                        "category": ap.get("category", "景点"),
                        "description": ap.get("description", ""),
                        "source": "xiaohongshu",
                        "popularity_hint": ap.get("popularity_hint", ""),
                        "tips": ap.get("tips", ""),
                    }
                    places.append(place)
            
            # 同时保留爬虫直接获取的数据（作为补充）
            for note in all_notes:
                name = note.get("name", "")
                if name and name not in {p.get("name") for p in places}:
                    places.append(note)
        
        # 去重
        seen_names = set()
        unique_places = []
        for p in places:
            name = p.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                unique_places.append(p)
        
        places = unique_places
        messages.append(f"📍 小红书共发现 {len(places)} 个地点")
        
    except Exception as e:
        messages.append(f"❌ 小红书搜索出错: {str(e)}")
    
    return {
        **state,
        "places": places,
        "messages": messages,
        "current_step": "xiaohongshu_done",
    }


async def dianping_node(state: TripPlannerState) -> TripPlannerState:
    """大众点评节点 - 补充商家详情"""
    location = state["location"]
    places = list(state.get("places", []))
    messages = list(state.get("messages", []))
    
    messages.append("🔍 正在大众点评补充详细信息...")
    
    try:
        # 提取城市名
        city = location[:2] if len(location) >= 2 else location
        
        # 为每个地点查询详情
        updated_count = 0
        for place in places:
            name = place.get("name", "")
            if not name:
                continue
            
            # 查询点评信息
            detail = await dianping_scraper.get_shop_detail(name, city)
            if detail:
                # 合并信息
                place["rating"] = detail.get("rating", place.get("rating"))
                place["price_range"] = detail.get("price_range", place.get("price_range"))
                place["address"] = detail.get("address", place.get("address"))
                if detail.get("category"):
                    place["category"] = detail["category"]
                updated_count += 1
            
            await asyncio.sleep(0.5)  # 避免请求过快
        
        messages.append(f"  ✅ 成功补充 {updated_count} 个地点的详细信息")
        
    except Exception as e:
        messages.append(f"❌ 大众点评查询出错: {str(e)}")
    
    return {
        **state,
        "places": places,
        "messages": messages,
        "current_step": "dianping_done",
    }


async def map_node(state: TripPlannerState) -> TripPlannerState:
    """地图节点 - 获取坐标和距离"""
    location = state["location"]
    places = list(state.get("places", []))
    messages = list(state.get("messages", []))
    
    messages.append("🗺️ 正在获取地理位置信息...")
    
    try:
        city = location[:2] if len(location) >= 2 else location
        geocoded_count = 0
        
        for place in places:
            if place.get("latitude") and place.get("longitude"):
                continue
            
            name = place.get("name", "")
            address = place.get("address", name)
            
            # 地理编码
            coords = await amap_service.geocode(f"{city}{address}", city)
            if coords:
                place["longitude"], place["latitude"] = coords
                geocoded_count += 1
            
            await asyncio.sleep(0.2)
        
        messages.append(f"  ✅ 成功定位 {geocoded_count} 个地点")
        
        # 使用POI搜索补充未找到的地点
        unlocated = [p for p in places if not p.get("latitude")]
        if unlocated:
            messages.append(f"  🔍 尝试通过POI搜索定位 {len(unlocated)} 个地点...")
            for place in unlocated:
                name = place.get("name", "")
                pois = await amap_service.poi_search(name, city, page_size=1)
                if pois:
                    poi = pois[0]
                    place["latitude"] = poi.get("latitude")
                    place["longitude"] = poi.get("longitude")
                    place["address"] = poi.get("address", place.get("address"))
        
    except Exception as e:
        messages.append(f"❌ 地理编码出错: {str(e)}")
    
    return {
        **state,
        "places": places,
        "messages": messages,
        "current_step": "map_done",
    }


async def planner_node(state: TripPlannerState) -> TripPlannerState:
    """规划节点 - 生成最终行程"""
    location = state["location"]
    places = list(state.get("places", []))
    start_time = state.get("start_time", "09:00")
    messages = list(state.get("messages", []))
    
    messages.append("📋 正在规划一日行程...")
    
    try:
        # 筛选有效地点（有坐标的）
        valid_places = [p for p in places if p.get("latitude") and p.get("longitude")]
        
        if not valid_places:
            messages.append("⚠️ 没有足够的有效地点来规划行程")
            return {
                **state,
                "messages": messages,
                "current_step": "planner_done",
                "error": "没有足够的有效地点",
            }
        
        # 调用LLM规划行程
        plan_result = await llm_service.plan_trip(valid_places, location, start_time)
        
        # 构建行程
        stops = []
        for stop_data in plan_result.get("stops", []):
            # 查找对应的地点信息
            place_name = stop_data.get("name", "")
            place_info = next((p for p in valid_places if p.get("name") == place_name), None)
            
            if place_info:
                stops.append({
                    "place": place_info,
                    "arrival_time": stop_data.get("arrival_time", ""),
                    "stay_duration": stop_data.get("stay_duration", 60),
                    "activity": stop_data.get("activity", ""),
                })
        
        # 计算路线距离
        total_distance = 0
        total_duration = 0
        
        for i in range(len(stops) - 1):
            current = stops[i]["place"]
            next_stop = stops[i + 1]["place"]
            
            if current.get("latitude") and next_stop.get("latitude"):
                origin = (current["longitude"], current["latitude"])
                dest = (next_stop["longitude"], next_stop["latitude"])
                
                distance_info = await amap_service.get_distance(origin, dest, "walking")
                stops[i]["distance_to_next"] = distance_info.get("distance", 0)
                stops[i]["duration_to_next"] = distance_info.get("duration", 0)
                stops[i]["transport_to_next"] = "步行"
                
                total_distance += distance_info.get("distance", 0)
                total_duration += stops[i]["stay_duration"] + distance_info.get("duration", 0)
        
        # 最后一站的停留时间
        if stops:
            total_duration += stops[-1]["stay_duration"]
        
        plan = {
            "location": location,
            "date": "今天",
            "stops": stops,
            "total_distance": total_distance,
            "total_duration": total_duration,
            "tips": plan_result.get("tips", ""),
        }
        
        messages.append(f"  ✅ 成功规划 {len(stops)} 个站点的行程")
        messages.append(f"  📏 总距离: {total_distance/1000:.1f}公里, 预计时长: {total_duration//60}小时{total_duration%60}分钟")
        
    except Exception as e:
        messages.append(f"❌ 行程规划出错: {str(e)}")
        plan = None
    
    return {
        **state,
        "plan": plan,
        "messages": messages,
        "current_step": "planner_done",
    }


def create_trip_planner_graph() -> StateGraph:
    """创建行程规划工作流图"""
    
    # 创建状态图
    workflow = StateGraph(TripPlannerState)
    
    # 添加节点
    workflow.add_node("xiaohongshu", xiaohongshu_node)
    workflow.add_node("dianping", dianping_node)
    workflow.add_node("map", map_node)
    workflow.add_node("planner", planner_node)
    
    # 定义边（工作流顺序）
    workflow.set_entry_point("xiaohongshu")
    workflow.add_edge("xiaohongshu", "dianping")
    workflow.add_edge("dianping", "map")
    workflow.add_edge("map", "planner")
    workflow.add_edge("planner", END)
    
    return workflow.compile()


# 编译工作流
trip_planner = create_trip_planner_graph()


async def run_trip_planner(location: str, preferences: List[str] = None, start_time: str = "09:00") -> dict:
    """运行行程规划器
    
    Args:
        location: 目的地，如"杭州西湖"
        preferences: 偏好标签
        start_time: 出发时间
    
    Returns:
        规划结果
    """
    initial_state: TripPlannerState = {
        "location": location,
        "preferences": preferences or [],
        "start_time": start_time,
        "places": [],
        "current_step": "init",
        "messages": [],
        "error": None,
        "plan": None,
    }
    
    # 运行工作流
    result = await trip_planner.ainvoke(initial_state)
    
    # 将 LangGraph 的 Message 对象转换为字符串
    raw_messages = result.get("messages", [])
    messages = []
    for msg in raw_messages:
        if hasattr(msg, 'content'):
            messages.append(str(msg.content))
        else:
            messages.append(str(msg))
    
    return {
        "success": result.get("error") is None,
        "places": result.get("places", []),
        "plan": result.get("plan"),
        "messages": messages,
        "error": result.get("error"),
    }
