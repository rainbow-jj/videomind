from pydantic import BaseModel
from app.schemas.clip import ClipOut

class AskIn(BaseModel):
    video_id: str
    question: str
    every_n_seconds: float = 1.0

class AskOut(BaseModel):
    answer: str
    clips: list[ClipOut]