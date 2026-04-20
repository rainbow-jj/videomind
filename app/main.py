from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import os

from app.core.config import settings
from app.api.routes import video, chat

# 创建上传目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于多模态大模型的视频智能分析与问答系统",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 跨域配置（前端开发时需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(video.router, prefix="/api/v1/videos", tags=["视频管理"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["智能问答"])

@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

logger.info(f"🚀 {settings.PROJECT_NAME} 启动成功")
