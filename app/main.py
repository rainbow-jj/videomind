from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import os

from app.core.config import settings
from app.core.db import engine, Base
from app.api.routes import video, chat, jobs, videos_extra

# 确保模型被导入，Base.metadata.create_all 才能创建表
from app.models.video import Video  # noqa: F401
from app.models.frame import VideoFrame  # noqa: F401
from app.models.processing_job import ProcessingJob  # noqa: F401
from app.models.job_stage import JobStage  # noqa: F401  # 如果你已新增

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于多模态大模型的视频智能分析与问答系统",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 只保留这一组路由注册
app.include_router(video.router, prefix="/api/v1/videos", tags=["视频管理"])
app.include_router(videos_extra.router, prefix="/api/v1/videos", tags=["视频管理"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["智能问答"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["任务管理"])


@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.on_event("startup")
async def on_startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"DATABASE_URL = {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


logger.info(f"🚀 {settings.PROJECT_NAME} 启动成功")