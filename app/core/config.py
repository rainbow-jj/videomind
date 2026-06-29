from pydantic_settings import BaseSettings
from pathlib import Path
from typing import ClassVar

class Settings(BaseSettings):
    BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parents[2]

    PROJECT_NAME: str = "VideoMind"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_FILE_SIZE: int = 500 * 1024 * 1024

    DASHSCOPE_API_KEY: str = ""
    VLM_BASE_URL:str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VLM_MODEL:str = "qwen2.5-vl-72b-instruct"
    # 现有（可先保留 sqlite）
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'videomind.db').as_posix()}"

    # 新增：为后续升级做准备
    SYNC_DATABASE_URL:str = f"sqlite:///{(BASE_DIR / 'videomind.db').as_posix()}"
    REDIS_URL:str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL:str = "redis://127.0.0.1:6379/1"
    CELERY_RESULT_BACKEND:str  = "redis://127.0.0.1:6379/2"

    QDRANT_URL:str = "http://127.0.0.1:6333"
    QDRANT_COLLECTION:str = "video_frames"

    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "videomind"

    LOG_LEVEL:str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore" # 关键：避免 .env 有未声明变量时报错（ 可选但推荐）

settings = Settings()