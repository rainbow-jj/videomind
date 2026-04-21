from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from loguru import logger
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.video import Video
from app.schemas.video import VideoOut

router = APIRouter()


@router.post("/upload", response_model=VideoOut)
async def upload_video(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
):
    """
    上传视频文件
    - 支持 mp4, avi, mov 格式
    - 最大 500MB
    """
    # 检查文件格式
    allowed_types = ["video/mp4", "video/avi", "video/quicktime"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file.content_type}，请上传 mp4/avi/mov"
        )

    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] or ".mp4"  # 默认使用 .mp4 扩展名
    stored_filename = f"{file_id}{file_ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")

    # 保存文件
    content = await file.read()
    # 检查文件大小
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件太大，最大支持500MB")

    with open(save_path, "wb") as f:
        f.write(content)

    video = Video(
        id=file_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        path=save_path,
        size=len(content),
        content_type=file.content_type,
        status="uploaded",
    )

    db.add(video)
    await db.commit()
    await db.refresh(video)

    logger.info(f"视频上传成功: {file_id}, 文件名: {file.filename}")
    return video

@router.get("/", response_model=list[VideoOut])
async def list_videos(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Video).order_by(Video.created_at.desc()))
        videos = result.scalars().all()
        return list(videos)

@router.get("/{video_id}", response_model=VideoOut)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="视频未找到")
    return video