from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Set
from pydantic import BaseModel, Field, model_validator
from bridge.nights import nights
from app.schemas.guests import GuestRead
from app.schemas.properties import RoomRead

class BookingStatus(str, Enum):
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    cancelled = "cancelled"
    no_show = "no_show"

# State machine transition rules from bridge/ex4_enum.py
ALLOWED_TRANSITIONS: dict[BookingStatus, Set[BookingStatus]] = {
    BookingStatus.confirmed: {
        BookingStatus.checked_in,
        BookingStatus.cancelled,
        BookingStatus.no_show
    },
    BookingStatus.checked_in: {
        BookingStatus.checked_out
    },
    BookingStatus.checked_out: set(),
    BookingStatus.cancelled: set(),
    BookingStatus.no_show: set(),
}

def can_transition(current: BookingStatus, target: BookingStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())

class BookingCreate(BaseModel):
    guest_id: int
    room_id: int
    check_in: date
    check_out: date
    guests_count: int = Field(gt=0, description="Must be at least 1 guest")
    nightly_rate: Optional[Decimal] = Field(default=None, gt=0, description="Override rate or fetch from rate plan")
    
    # Optional deposit payment for atomic booking + payment transaction (Rule 8 / Task 6)
    deposit_amount: Optional[Decimal] = Field(default=None, gt=0)
    deposit_method: Optional[str] = Field(default=None, pattern="^(card|upi|bank_transfer|cash)$")
    idempotency_key: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates_and_nights(self):
        try:
            n = nights(self.check_in, self.check_out)
        except ValueError as e:
            raise ValueError(str(e))
        return self

class BookingStatusUpdate(BaseModel):
    status: BookingStatus

class BookingRead(BaseModel):
    booking_id: int
    guest_id: int
    room_id: int
    check_in: date
    check_out: date
    stay_str: Optional[str] = None
    nights: int
    guests_count: int
    nightly_rate: Decimal
    total_amount: Decimal
    status: BookingStatus
    created_at: str
    guest: Optional[GuestRead] = None
    room: Optional[RoomRead] = None
    payments_total: Optional[Decimal] = Decimal("0.00")
    is_fully_paid: Optional[bool] = False

class AvailabilityQuery(BaseModel):
    check_in: date
    check_out: date
    property_id: Optional[int] = None
    guests_count: Optional[int] = 1

    @model_validator(mode="after")
    def validate_stay(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self
