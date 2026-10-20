from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field

class RoomTypeRead(BaseModel):
    room_type_id: int
    name: str
    max_occupancy: int

class RoomRead(BaseModel):
    room_id: int
    property_id: int
    room_number: str
    room_type_id: int
    room_type_name: Optional[str] = None
    max_occupancy: Optional[int] = None

class PropertyBase(BaseModel):
    name: str
    city: str
    star_rating: int = Field(ge=1, le=5)

class PropertyRead(PropertyBase):
    property_id: int
    rooms: Optional[List[RoomRead]] = None

class RatePlanRead(BaseModel):
    rate_plan_id: int
    property_id: int
    room_type_id: int
    season_name: str
    valid_from: str
    valid_to: str
    nightly_rate: Decimal
