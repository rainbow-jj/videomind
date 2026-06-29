from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.job import (
    APIResponse,
    VideoTimelineOut,
    TimelineItemOut,
    HybridSearchOut,
    HybridSearchItemOut,
)

router = APIRouter()


@router.get("/{video_id}/timeline", response_model=APIResponse)
async def get_timeline(video_id: str, db: AsyncSession = Depends(get_db)):
    # 先用最保守字段，避免不存在列导致500
    rows = (
        await db.execute(
            text("""
                SELECT id, timestamp, image_url, caption
                FROM video_frames
                WHERE video_id = :video_id
                ORDER BY timestamp ASC
                LIMIT 1000
            """),
            {"video_id": video_id},
        )
    ).mappings().all()

    items = [
        TimelineItemOut(
            timestamp=float(r["timestamp"]) if r.get("timestamp") is not None else 0.0,
            frame_id=str(r["id"]),
            image_url=r.get("image_url"),
            caption=r.get("caption"),
            score=None,  # 先置空，确认接口可用
        )
        for r in rows
    ]

    return APIResponse(data=VideoTimelineOut(video_id=video_id, duration=None, items=items))


@router.get("/{video_id}/search-hybrid", response_model=APIResponse)
async def search_hybrid(
    video_id: str,
    q: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            text("""
                SELECT id, timestamp, caption
                FROM video_frames
                WHERE video_id = :video_id
                  AND caption ILIKE :kw
                ORDER BY timestamp ASC
                LIMIT :top_k
            """),
            {"video_id": video_id, "kw": f"%{q}%", "top_k": top_k},
        )
    ).mappings().all()

    items = [
        HybridSearchItemOut(
            type="frame",
            video_id=video_id,
            frame_id=str(r["id"]),
            timestamp=float(r["timestamp"]) if r.get("timestamp") is not None else None,
            text=r.get("caption"),
            score=0.8,
        )
        for r in rows
    ]

    return APIResponse(data=HybridSearchOut(query=q, items=items))