from datetime import datetime
from pydantic import BaseModel

class VideoOut(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    path: str
    size: int
    content_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True