"""数据模型定义"""
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class PlaceCategory(str, Enum):
    """地点分类"""
    ATTRACTION = "景点"
    FOOD = "美食"
    SHOPPING = "购物"
    ENTERTAINMENT = "娱乐"


class DataSource(str, Enum):
    """数据来源"""
    XIAOHONGSHU = "xiaohongshu"
    DIANPING = "dianping"
    AMAP = "amap"


class PlaceInfo(BaseModel):
    """地点信息"""
    name: str = Field(..., description="地点名称")
    category: PlaceCategory = Field(..., description="分类")
    description: str = Field(default="", description="描述")
    source: DataSource = Field(..., description="数据来源")
    
    # 小红书数据
    likes: Optional[int] = Field(default=None, description="点赞数")
    note_url: Optional[str] = Field(default=None, description="笔记链接")
    
    # 大众点评数据
    rating: Optional[float] = Field(default=None, description="评分")
    price_range: Optional[str] = Field(default=None, description="人均消费")
    opening_hours: Optional[str] = Field(default=None, description="营业时间")
    
    # 地图数据
    address: Optional[str] = Field(default=None, description="地址")
    latitude: Optional[float] = Field(default=None, description="纬度")
    longitude: Optional[float] = Field(default=None, description="经度")


class TripStop(BaseModel):
    """行程站点"""
    place: PlaceInfo = Field(..., description="地点信息")
    arrival_time: str = Field(..., description="到达时间")
    stay_duration: int = Field(..., description="停留时长(分钟)")
    transport_to_next: Optional[str] = Field(default=None, description="到下一站的交通方式")
    distance_to_next: Optional[float] = Field(default=None, description="到下一站距离(米)")
    duration_to_next: Optional[int] = Field(default=None, description="到下一站时间(分钟)")


class TripPlan(BaseModel):
    """行程规划"""
    location: str = Field(..., description="目的地")
    date: str = Field(..., description="日期")
    stops: List[TripStop] = Field(default_factory=list, description="行程站点列表")
    total_distance: float = Field(default=0, description="总距离(米)")
    total_duration: int = Field(default=0, description="总时长(分钟)")


class PlanRequest(BaseModel):
    """规划请求"""
    location: str = Field(..., description="目的地，如'杭州西湖'")
    preferences: Optional[List[str]] = Field(default=None, description="偏好标签")
    start_time: str = Field(default="09:00", description="出发时间")


class AgentState(BaseModel):
    """LangGraph Agent状态"""
    request: PlanRequest = Field(..., description="用户请求")
    places: List[PlaceInfo] = Field(default_factory=list, description="收集到的地点")
    plan: Optional[TripPlan] = Field(default=None, description="最终行程")
    current_step: str = Field(default="init", description="当前步骤")
    messages: List[str] = Field(default_factory=list, description="处理消息")
    error: Optional[str] = Field(default=None, description="错误信息")
