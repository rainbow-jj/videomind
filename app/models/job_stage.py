from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class JobStage(Base):
    __tablename__ = "job_stages"

    id = Column(String(36), primary_key=True, index=True) #uuid
    job_id = Column(String(36), ForeignKey("processing_jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    stage = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, done, failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)  # 处理中的消息或错误信息

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)