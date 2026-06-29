from datetime import datetime
from pydantic import BaseModel
from typing import List


class FrameHitOut(BaseModel):
    id: str
    video_id: str
    timestamps_ms: int
    image_path: str
    caption: str

class ClipOut(BaseModel):
    start_ms: int
    end_ms: int
    hit_count: int
    frames: List[FrameHitOut]   # 关键：这里必须是 FrameHitOut

class ChatAskIn(BaseModel):
    video_id: str
    question: str
    every_n_seconds: float = 1.0


class ChatAskOut(BaseModel):
    answer: str
    clips: List[ClipOut]


class VideoOut(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    path: str
    size: int
    content_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# 分页响应器模型
class VideoListResponse(BaseModel):
    items: list[VideoOut]
    total: int
    page: int
    page_size: int