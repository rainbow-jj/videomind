from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 项目基础配置
    PROJECT_NAME: str = "VideoMind"
    VERSION:str  = "0.1.0"
    DEBUG: bool = True

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

    # 通义千问配置
    DASHSCOPE_API_KEY: str = ""

    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./videomind.db"

    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局配置实例
settings = Settings()
