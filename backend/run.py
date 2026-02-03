"""
Day Trip Planner - Server Entry Point
使用 Hypercorn 运行 FastAPI 应用，支持 Windows Playwright
"""
import sys
import asyncio

# Windows 平台必须在任何其他导入之前设置 ProactorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from hypercorn.config import Config
from hypercorn.asyncio import serve

# 现在可以安全导入 FastAPI 应用
from main import app


async def main():
    """Run the server with Hypercorn"""
    config = Config()
    config.bind = ["127.0.0.1:8000"]
    config.use_reloader = True  # 开发模式下自动重载
    config.accesslog = "-"  # 输出访问日志到 stdout
    
    print("=" * 50)
    print("🚀 Day Trip Planner API Starting...")
    print("📍 Server: http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("=" * 50)
    
    await serve(app, config)


if __name__ == "__main__":
    asyncio.run(main())
