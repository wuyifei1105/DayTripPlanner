"""FastAPI主应用入口"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os

from agents.workflow import run_trip_planner
from models.schemas import PlanRequest


app = FastAPI(
    title="一日行程规划 API",
    description="基于Multi-Agent的一日行程规划服务",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PlanResponse(BaseModel):
    """规划响应"""
    success: bool
    places: List[dict]
    plan: Optional[dict]
    messages: List[str]
    error: Optional[str]


@app.get("/")
async def root():
    """首页"""
    return {"message": "一日行程规划 API", "docs": "/docs"}


@app.post("/api/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """创建行程规划
    
    Args:
        request: 规划请求，包含目的地、偏好等
    
    Returns:
        规划结果，包含地点列表和行程安排
    """
    try:
        result = await run_trip_planner(
            location=request.location,
            preferences=request.preferences,
            start_time=request.start_time,
        )
        return PlanResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# 挂载前端静态文件
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/app")
    async def serve_frontend():
        """提供前端页面"""
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
