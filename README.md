# 一日行程规划 - Multi-Agent 产品

基于 LangGraph 的多 Agent 协作系统，自动从小红书、大众点评获取推荐信息，结合高德地图生成完美的一日游行程。

## ✨ 功能特点

- 🔍 **智能搜索** - 自动从小红书搜索热门景点和美食
- ⭐ **信息补充** - 从大众点评获取评分、价格、营业时间
- 🗺️ **地图定位** - 高德地图API定位和路线规划
- 📋 **智能规划** - AI自动生成合理的一日行程
- 🔐 **一次登录** - Playwright Session持久化，只需登录一次

## 🏗️ 技术架构

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   Frontend  │────▶│           Backend (FastAPI)          │
│  HTML/CSS/JS│     │                                     │
└─────────────┘     │  ┌─────────────────────────────┐   │
                    │  │      LangGraph Workflow      │   │
                    │  │  ┌─────┐ ┌─────┐ ┌─────┐    │   │
                    │  │  │ XHS │─▶│DP  │─▶│Map │    │   │
                    │  │  └─────┘ └─────┘ └─────┘    │   │
                    │  │           ▼                  │   │
                    │  │       ┌────────┐            │   │
                    │  │       │Planner │            │   │
                    │  │       └────────┘            │   │
                    │  └─────────────────────────────┘   │
                    └─────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

已在 `.env` 文件中配置好API Keys：
- NVIDIA NIM API (LLM推理)
- 高德地图API (地图服务)

### 3. 启动后端服务

```bash
cd backend
uvicorn main:app --reload
```

### 4. 访问前端

打开浏览器访问: http://localhost:8000/app

或者直接打开 `frontend/index.html`

## 📖 使用说明

1. 输入目的地（如"杭州西湖"）
2. 设置出发时间
3. 点击"开始规划"
4. **首次使用**会弹出浏览器窗口，需要登录小红书和大众点评
5. 登录后按回车继续，之后不需要再登录
6. 等待系统自动搜索和规划
7. 查看地点列表、地图和行程时间轴

## 📁 项目结构

```
DayTripPlanner/
├── backend/
│   ├── agents/
│   │   ├── workflow.py      # LangGraph工作流
│   │   └── __init__.py
│   ├── scrapers/
│   │   ├── browser_manager.py    # 浏览器会话管理
│   │   ├── xiaohongshu_scraper.py
│   │   └── dianping_scraper.py
│   ├── services/
│   │   ├── llm_service.py   # NVIDIA NIM API
│   │   └── amap_service.py  # 高德地图API
│   ├── models/
│   │   └── schemas.py       # 数据模型
│   ├── main.py              # FastAPI入口
│   ├── config.py            # 配置管理
│   ├── .env                 # 环境变量
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js
│       ├── map.js
│       └── app.js
├── browser_data/            # 浏览器Session存储
└── README.md
```

## ⚠️ 注意事项

1. 首次运行需要登录小红书和大众点评
2. 登录信息保存在 `browser_data/` 目录
3. 小红书和大众点评有反爬机制，请勿频繁请求
4. 如遇到验证码，请手动处理后按回车继续

## 📝 License

MIT
