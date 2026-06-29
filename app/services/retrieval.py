from typing import List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.frame import VideoFrame
from app.schemas.video import ClipOut, FrameHitOut

def _to_frame_hit(x: VideoFrame) -> FrameHitOut:
    return FrameHitOut(
        id=str(x.id),
        video_id=str(x.video_id),
        timestamps_ms=int(x.timestamps_ms or 0),
        image_path=x.image_path or "",
        caption=x.caption or "",

    )

def _group_frames_to_clips(
        frames: List[VideoFrame],
        gap_ms:int,
        pad_ms:int,
        max_frames_per_clip:int = 5,
) -> List[ClipOut]:
    if not frames:
        return []

    groups = []
    cur = [frames[0]]
    for f in frames[1:]:
        if f.timestamps_ms - cur[-1].timestamps_ms <= gap_ms:
            cur.append(f)
        else:
            groups.append(cur)
            cur = [f]
    groups.append(cur)

    clips: List[ClipOut] = []
    for g in groups:
        start_ms = max(0, int(g[0].timestamps_ms) - pad_ms)
        end_ms = int(g[-1].timestamps_ms) + pad_ms
        frames_out = [_to_frame_hit(x) for x in g[:max_frames_per_clip]]

        clips.append(
            ClipOut(
                start_ms=start_ms,
                end_ms=end_ms,
                hit_count=len(g),
                frames=frames_out,
            )
        )

        # Day9 排序优化(命中多优先、其次时长长短优先）
        clips.sort(key=lambda c: (-c.hit_count, (c.end_ms - c.start_ms)))
        return clips



async def search_clips_service(
    db: AsyncSession,
    video_id: str,
    q: str,
    every_n_seconds: float = 1.0,
    gap_multiplier: float = 2.5,
    pad_ms: int = 1500,
) -> List[ClipOut]:
    """
    -支持多关键词 OR 匹配
    -SQLite 兼容匹配 （lower + like)
    """
    base_stmt = (
        select(VideoFrame)
        .where(VideoFrame.video_id == video_id)
        .order_by(VideoFrame.timestamps_ms.asc())
    )

    terms = [t.strip().lower() for t in (q or "").split() if t.strip()]
    if terms:
        text_col = func.lower(func.coalesce(VideoFrame.caption, ""))
        conds = [text_col.like(f"%{t}%") for t in terms]
        base_stmt = base_stmt.where(or_(*conds))

    result = await db.execute(base_stmt)
    hits = list(result.scalars().all())
    if not hits:
        return []

    gap_ms = int(every_n_seconds * 1000 * gap_multiplier)
    return _group_frames_to_clips(
        frames=hits,
        gap_ms=gap_ms,
        pad_ms=pad_ms,
        max_frames_per_clip=5,
    )