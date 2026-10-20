from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(ge=1, le=5, description="Rating must be between 1 and 5")
    comments: Optional[str] = None

class ReviewRead(BaseModel):
    review_id: int
    booking_id: int
    rating: int
    comments: Optional[str] = None
    reviewed_at: Union[datetime, str]
