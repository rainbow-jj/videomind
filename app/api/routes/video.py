from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger
import os
import uuid
from app.core.config import settings

router = APIRouter()


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
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
    file_ext = os.path.splitext(file.filename)[1]
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")

    # 保存文件
    content = await file.read()

    # 检查文件大小
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件太大，最大支持500MB")

    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"视频上传成功: {file_id}, 文件名: {file.filename}")

    return {
        "video_id": file_id,
        "filename": file.filename,
        "size": len(content),
        "status": "uploaded",
        "message": "上传成功，等待分析"
    }


@router.get("/")
async def list_videos():
    """获取所有视频列表"""
    # 简单实现，直接读取uploads目录
    videos = []
    for filename in os.listdir(settings.UPLOAD_DIR):
        if filename.endswith(('.mp4', '.avi', '.mov')):
            video_id = os.path.splitext(filename)[0]
            videos.append({
                "video_id": video_id,
                "filename": filename,
                "status": "uploaded"
            })
    return {"videos": videos, "total": len(videos)}


@router.get("/{video_id}")
async def get_video(video_id: str):
    """获取单个视频信息"""
    # 查找文件
    for ext in ['.mp4', '.avi', '.mov']:
        file_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")
        if os.path.exists(file_path):
            return {
                "video_id": video_id,
                "filename": f"{video_id}{ext}",
                "status": "uploaded"
            }

    raise HTTPException(status_code=404, detail="视频不存在")