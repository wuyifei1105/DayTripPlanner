"""高德地图API服务封装"""
from typing import List, Dict, Any, Optional, Tuple
import httpx
from config import settings


class AmapService:
    """高德地图API封装"""
    
    BASE_URL = "https://restapi.amap.com/v3"
    
    def __init__(self):
        self.api_key = settings.amap_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """发送API请求"""
        params["key"] = self.api_key
        params["output"] = "json"
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") != "1":
            raise Exception(f"高德API错误: {data.get('info', '未知错误')}")
        
        return data
    
    async def geocode(self, address: str, city: str = "") -> Optional[Tuple[float, float]]:
        """地理编码：地址转坐标"""
        params = {"address": address}
        if city:
            params["city"] = city
        
        try:
            data = await self._request("geocode/geo", params)
            geocodes = data.get("geocodes", [])
            if geocodes:
                location = geocodes[0].get("location", "")
                if location:
                    lng, lat = location.split(",")
                    return float(lng), float(lat)
        except Exception:
            pass
        return None
    
    async def poi_search(
        self,
        keywords: str,
        city: str,
        types: str = "",
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """POI搜索"""
        params = {
            "keywords": keywords,
            "city": city,
            "citylimit": "true",
            "page": page,
            "offset": page_size,
            "extensions": "all",
        }
        if types:
            params["types"] = types
        
        try:
            data = await self._request("place/text", params)
            pois = data.get("pois", [])
            
            results = []
            for poi in pois:
                location = poi.get("location", "")
                lng, lat = (0.0, 0.0)
                if location:
                    lng, lat = map(float, location.split(","))
                
                results.append({
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "type": poi.get("type", ""),
                    "latitude": lat,
                    "longitude": lng,
                    "tel": poi.get("tel", ""),
                    "rating": poi.get("biz_ext", {}).get("rating", ""),
                    "cost": poi.get("biz_ext", {}).get("cost", ""),
                    "opening_hours": poi.get("biz_ext", {}).get("opentime", ""),
                })
            
            return results
        except Exception as e:
            print(f"POI搜索失败: {e}")
            return []
    
    async def get_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str = "walking"  # walking, driving, transit
    ) -> Dict[str, Any]:
        """计算两点间距离和时间"""
        origin_str = f"{origin[0]},{origin[1]}"
        dest_str = f"{destination[0]},{destination[1]}"
        
        if mode == "walking":
            endpoint = "direction/walking"
        elif mode == "driving":
            endpoint = "direction/driving"
        else:
            endpoint = "direction/transit/integrated"
        
        params = {
            "origin": origin_str,
            "destination": dest_str,
        }
        
        try:
            data = await self._request(endpoint, params)
            
            if mode in ["walking", "driving"]:
                route = data.get("route", {})
                paths = route.get("paths", [])
                if paths:
                    path = paths[0]
                    return {
                        "distance": int(path.get("distance", 0)),
                        "duration": int(path.get("duration", 0)) // 60,  # 转换为分钟
                        "mode": mode,
                    }
            
            return {"distance": 0, "duration": 0, "mode": mode}
        except Exception as e:
            print(f"距离计算失败: {e}")
            return {"distance": 0, "duration": 0, "mode": mode}
    
    async def batch_geocode(self, places: List[Dict], city: str) -> List[Dict]:
        """批量获取地点坐标"""
        results = []
        for place in places:
            name = place.get("name", "")
            address = place.get("address", name)
            
            coords = await self.geocode(f"{city}{address}", city)
            if coords:
                place["longitude"], place["latitude"] = coords
            
            results.append(place)
        
        return results
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局实例
amap_service = AmapService()
