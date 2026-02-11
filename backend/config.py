"""配置管理模块"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    # NVIDIA API配置
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_base_url: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "qwen/qwen3-next-80b-a3b-thinking")
    
    # 高德地图API配置
    amap_api_key: str = os.getenv("AMAP_API_KEY", "")
    
    # 小红书 Cookie（从浏览器 F12 获取登录后的 cookie）
    xhs_cookies: str = os.getenv("XHS_COOKIES", "")
    
    class Config:
        env_file = ".env"


settings = Settings()

