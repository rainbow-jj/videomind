from fastapi import APIRouter
from . import video, chat, jobs, videos_extra

api_router = APIRouter()
api_router.include_router(video.router)
api_router.include_router(chat.router)
api_router.include_router(jobs.router)