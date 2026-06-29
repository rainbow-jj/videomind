from fastapi import APIRouter, UploadFile, File, HTTPException, Depends,Query
from loguru import logger
import os
import uuid
import re
import aiofiles

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.db import get_db
from app.models.video import Video
from app.schemas.video import VideoOut, FrameHitOut, ClipOut, VideoListResponse
from app.models.frame import VideoFrame
from app.schemas.frame import FrameOut
from app.services.captioner import generate_caption
from app.services.retrieval import search_clips_service

from datetime import datetime
from app.services.frame_extractor import extract_frames_every_n_seconds

router = APIRouter()


# 上传
@router.post("/upload", response_model=VideoOut, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # 1. 先校验格式（不读文件内容）
    allowed_types = ["video/mp4", "video/avi", "video/quicktime"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file.content_type}，请上传 mp4/avi/mov"
        )

    # 2. 生成文件名
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] or ".mp4"
    stored_filename = f"{file_id}{file_ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    try:
        # 3. 流式写入（每次读1MB，边读边写，不占满内存）
        file_size = 0
        async with aiofiles.open(save_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 每次1MB
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE:
                    # 文件太大，删除已写入的部分
                    await f.close()
                    os.remove(save_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件太大，最大支持 {settings.MAX_FILE_SIZE // 1024 // 1024}MB"
                    )
                await f.write(chunk)

        # 4. 写数据库
        video = Video(
            id=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            path=save_path,
            size=file_size,
            content_type=file.content_type,
            status="uploaded",
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)

        logger.info(f"视频上传成功: {file_id}, 文件名: {file.filename}")
        return video

    except HTTPException:
        raise  # HTTP异常直接抛出
    except Exception as e:
        # 其他异常：回滚DB、删除文件、记录日志
        await db.rollback()
        if os.path.exists(save_path):
            os.remove(save_path)
        logger.error(f"视频上传失败: {e}")
        raise HTTPException(status_code=500, detail="上传失败，请稍后重试")


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    page:int = Query(1, ge=1, description="页码，从1开始"),
    page_size:int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    # 1. 查询总数
    total_result = await db.execute(select(func.count(Video.id))) # func.count(Video.if) SQL的COUNT(*),异步执行
    total = total_result.scalar() or 0

    # 2. 查询分页数据 (偏移量计算）
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Video)
        .order_by(Video.created_at.desc())
        .offset(offset)
        .limit(page_size) #offset(offset).limit(page_size) SQL分页，offset是跳过的条数
    )
    videos = result.scalars().all()

    return VideoListResponse(
        items=videos,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
        video_id: str,
        db: AsyncSession = Depends(get_db)
):
    # 1、查询数据库
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not Video:
        raise HTTPException(status_code=404, detail="视频未找到")

    # 2、校验文件是否存在
    if not os.path.exists(video.path):
        logger.warning(f"视频文件不存在: {video.path}")
        # 可以选择更新数据库状态
        video.status = "file_missing"
        await db.commit()

    return video

@router.post("/{video_id}/extract-frames")
async def extract_frames(video_id: str, every_n_seconds: float = 1.0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="视频未找到")

    if not os.path.exists(video.path):
        raise HTTPException(status_code=400, detail=f"视频文件不存在: {video.path}")

    # 输出目录：uploads/<video_id>/frames
    frames_dir = os.path.join(settings.UPLOAD_DIR, video.id, "frames")

    try:
        video.status = "processing"
        await db.commit()

        frame_count = extract_frames_every_n_seconds(video.path, frames_dir, every_n_seconds=every_n_seconds)

        video.frames_dir = frames_dir
        video.frame_count = frame_count
        video.processed_at = datetime.utcnow()
        video.status = "processed"

        await db.commit()
        await db.refresh(video)

        return {
            "video_id": video.id,
            "status": video.status,
            "frame_count": video.frame_count,
            "frames_dir": video.frames_dir,
        }
    except Exception as e:
        video.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{video_id}/frames")
async def list_frames(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="视频未找到")

    if not video.frames_dir or not os.path.isdir(video.frames_dir):
        return {"video_id": video.id, "frames": []}

    frames = sorted([f for f in os.listdir(video.frames_dir) if f.lower().endswith((".jpg", ".png"))])
    return {"video_id": video.id, "count": len(frames), "frames": frames[:50]}

# 把磁盘上的帧“同步入库”
@router.post("/{video_id}/sync-frames")
async def sync_frames(video_id: str, every_n_seconds: float = 1.0, db: AsyncSession = Depends(get_db)):
    frames_dir = Path(settings.UPLOAD_DIR) / video_id / "frames"
    if not frames_dir.exists():
        raise HTTPException(status_code=404, detail=f"frames目录不存在: {frames_dir}")

    image_files = sorted([p for p in frames_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    if not image_files:
        return {"video_id": video_id, "synced": 0 }


    # 取已存在的 frame_index, 避免重复插入
    existing = await db.execute(select(VideoFrame.timestamps_ms).where(VideoFrame.video_id == video_id))
    # existing_idx = set(existing.scalars().all())
    existing_ts = set(existing.scalars().all())

    synced = 0
    for p in image_files:
        m = re.search(r"(\d+)", p.stem) # 从文件名提取数字：000123 -> 000123
        if not m:
            continue
        count = int(m.group(1)) # 000123 -> 123

        ts_ms = int(round(count * every_n_seconds * 1000))
        if ts_ms in existing_ts:
            continue

        db.add(VideoFrame(
            video_id=video_id,
            timestamps_ms=ts_ms,
            image_path=str(p),
            caption="", # 后续可以添加字幕
        ))
        synced += 1

    await db.commit()
    return {"video_id": video_id, "synced": synced, "every_n_seconds": every_n_seconds}




# 关键词搜索
@router.get("/{video_id}/search", response_model=list[FrameOut])
async def search_frames(video_id: str, q: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(VideoFrame)
        .where(
            VideoFrame.video_id == video_id,
            VideoFrame.caption.ilike(f"%{q}%")
        )
        .order_by(VideoFrame.timestamps_ms.asc())
        .limit(50)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    # 关键：字段映射，避免 response_model 校验失败
    return [
        FrameOut(
            id=r.id,
            video_id=r.video_id,
            frame_index=getattr(r, "frame_index", int(r.timestamps_ms // 1000)),
            timestamps=float(r.timestamps_ms) / 1000.0,
            image_path=r.image_path,
            caption=r.caption or "",
            created_at=r.created_at,
        )
        for r in rows
    ]
def _group_frames_to_clips(frames, gap_ms: int, pad_ms: int, max_frames_per_clip: int = 5):
    clips = []
    if not frames:
        return clips

    current = [frames[0]]
    for f in frames[1:]:
        if f.timestamps_ms - current[-1].timestamps_ms <= gap_ms:
            current.append(f)
        else:
            clips.append(current)
            current = [f]
    clips.append(current)

    out = []
    for group in clips:
        start_ms = max(0, group[0].timestamps_ms - pad_ms)
        end_ms = group[-1].timestamps_ms + pad_ms
        out.append({
            "start_ms": start_ms,
            "end_ms": end_ms,
            "hit_count": len(group),
            "frames": group[:max_frames_per_clip],
        })
    return out

# 把命中帧聚成时间片段
@router.get("/{video_id}/search-clip", response_model=list[ClipOut]) # 输入问题、返回clips
async def search_clip(
        video_id: str,
        q: str,
        every_n_seconds: float = Query(1.0, ge=0.1, le=10.0),
        gap_multiplier: float = Query(2.5, ge=1.0, le=10.0),
        pad_ms: int = Query(1500, ge=0, le=10000),
        db: AsyncSession = Depends(get_db),
):
    return await search_clips_service(
        db=db,
        video_id=video_id,
        q=q,
        every_n_seconds=every_n_seconds,
        gap_multiplier=gap_multiplier,
        pad_ms=pad_ms
    )

# 给已经存在于数据库里的帧记录补齐/修正 timestamps_ms（帧在视频中的时间点）。
@router.post("/{video_id}/backfill-timestamps")
async def backfill_timestamps(video_id: str, every_n_seconds: float = 1.0, db: AsyncSession = Depends(get_db)):
    # 取出所有帧
    result = await db.execute(
        select(VideoFrame).where(VideoFrame.video_id == video_id)
        # .order_by(VideoFrame.frame_index.asc())
    )
    frames = result.scalars().all()
    if not frames:
        raise HTTPException(status_code=404, detail="视没有帧记录，请先调用 sync-frames")

    update = 0
    for f in frames:
        # 从 image_path 文件名中解析 000123.jpg -> 123
        stem = os.path.splitext(os.path.basename(f.image_path))[0]
        m = re.search(r"(\d+)", stem)
        if not m:
            continue
        count = int(m.group(1))
        ts_ms = int(round(count * every_n_seconds * 1000))

        # 只有变化才更新
        if f.timestamps_ms != ts_ms:
            f.timestamps_ms = ts_ms
            update += 1

    await db.commit()
    return {"video_id": video_id, "updated": len(frames), "every_n_seconds": every_n_seconds}


# 给视频帧批量生成文字描述（caption）并写回数据库。
@router.post("/{video_id}/caption-frames")
async def caption_frames(video_id: str,
                         limit:int = 20, # 本次最多处理多少帧
                         force:bool = False,
                         db: AsyncSession = Depends(get_db)):
    stmt = (
        select(VideoFrame)
        .where(VideoFrame.video_id == video_id, VideoFrame.caption == "")
        .order_by(VideoFrame.timestamps_ms.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    frames = list(result.scalars().all())
    if not frames:
        raise HTTPException(status_code=404, detail="没有帧记录，请先 sync-frames")

    updated = 0
    for f in frames:
        if f.caption and f.caption.strip() and not force:
            continue
        f.caption = generate_caption(f.image_path) # 这里调用一个假设的函数，实际应该接入一个图像字幕生成模型
        updated += 1
        if updated >= limit:
            break

    await db.commit()
    return {"video_id": video_id, "captioned": updated, "limit": limit, "force": force}

