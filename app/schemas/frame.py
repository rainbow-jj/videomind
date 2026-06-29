from datetime import datetime
from pydantic import BaseModel

class FrameOut(BaseModel):
    id: str
    video_id: str
    frame_index: int
    image_path: str
    caption: str
    created_at: datetime
    timestamps: int

    class Config:
        from_attributes = True