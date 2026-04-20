from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def chat_placeholder():
    """对话接口（下周实现）"""
    return {"message": "对话功能开发中"}