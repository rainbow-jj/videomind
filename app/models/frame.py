import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class VideoFrame(Base):
    __tablename__ = "video_frames"
    __table_args__ = (
        UniqueConstraint("video_id", "timestamps_ms", name="uq_video_frame_ts"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String(36), ForeignKey("videos.id"), nullable=False)

    timestamps_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # 帧对应的视频时间戳，单位毫秒
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # 存储帧图像的文件路径

    caption: Mapped[str] = mapped_column(String(4000), nullable=False, default="")  # 帧的字幕文本，可能为 null
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
