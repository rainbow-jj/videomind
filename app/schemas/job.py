from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class JobCreateIn(BaseModel):
    video_id: str
    job_type: str = "full_pipeline"


class JobOut(BaseModel):
    id: str
    video_id: str
    job_type: str
    status: str
    progress: int
    message: str = ""
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class APIResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any


# ===== 新增：Jobs 列表 =====
class JobListOut(BaseModel):
    items: List[JobOut]
    total: int
    page: int
    size: int


# ===== 新增：Stages =====
class JobStageOut(BaseModel):
    stage: str
    status: str
    progress: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


# ===== 新增：Retry =====
class JobRetryOut(BaseModel):
    job_id: str
    celery_task_id: Optional[str] = None
    status: str


# ===== 新增：Timeline =====
class TimelineItemOut(BaseModel):
    timestamp: float
    frame_id: str
    image_url: Optional[str] = None
    caption: Optional[str] = None
    score: Optional[float] = None


class VideoTimelineOut(BaseModel):
    video_id: str
    duration: Optional[float] = None
    items: List[TimelineItemOut]


# ===== 新增：Hybrid Search =====
class HybridSearchItemOut(BaseModel):
    type: str  # frame | clip
    video_id: str
    frame_id: Optional[str] = None
    timestamp: Optional[float] = None
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None
    text: Optional[str] = None
    score: float


class HybridSearchOut(BaseModel):
    query: str
    items: List[HybridSearchItemOut]