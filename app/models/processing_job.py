import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), nullable=False)

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="full_pipeline")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")  # queued/running/success/failed
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    celery_task_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


Index("idx_processing_jobs_video_id", ProcessingJob.video_id)
Index("idx_processing_jobs_status", ProcessingJob.status)