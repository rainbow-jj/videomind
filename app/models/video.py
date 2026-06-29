import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)

    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    frames_dir: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # 存储帧图像的目录路径
    frame_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)  # 视频的总帧数
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 视频处理完成的时间

    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")  # 处理失败时的错误信息
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
