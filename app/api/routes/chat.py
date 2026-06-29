from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.video import ChatAskOut, ChatAskIn
from app.services.retrieval import search_clips_service


# router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
router = APIRouter() 

@router.get("/")
async def chat_placeholder():
    """对话接口（下周实现）"""
    return {"message": "对话功能开发中"}

def _group_frames_to_clips(frames, gap_ms: int, pad_ms:int, max_frames_per_clip: int = 5):
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

@router.post("/ask", response_model=ChatAskOut)
async def ask(req: ChatAskIn, db: AsyncSession = Depends(get_db)):
    # 简化： 直接调用 search-cliop 的逻辑（建议提成 service）
    # 这里先写伪调用，你按项目结构改：
    clips = await search_clips_service(
        video_id=req.video_id,
        q=req.question,
        every_n_seconds=req.every_n_seconds,
        gap_multiplier=2.5,
        pad_ms=1500,
        db=db,
    )

    if not clips:
        return ChatAskOut(
            answer="未检索到相关片段。建议先执行 caption-frames 或更换关键词。",
            clips=[],
        )

    top = clips[0]
    evidence = [f.caption for f in top.frames[:2] if f.caption]
    evidence_text = ";".join(evidence) if evidence else "无可以用证据文本"


    answer = (f"找到 {len(clips)} 段相关片段，最相关片段约在"
              f"{top.start_ms/1000:.1f}s - {top.end_ms/1000:.1f}s。"
              f"依据：{evidence_text}"
              )
    return ChatAskOut(answer=answer, clips=clips)
