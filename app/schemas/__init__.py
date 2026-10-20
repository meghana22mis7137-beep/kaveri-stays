from app.schemas.common import ErrorDetail, MessageResponse
from app.schemas.properties import (
    PropertyBase, PropertyRead, RoomTypeRead, RoomRead, RatePlanRead
)
from app.schemas.guests import GuestBase, GuestCreate, GuestRead
from app.schemas.bookings import (
    BookingStatus, BookingCreate, BookingStatusUpdate, BookingRead,
    AvailabilityQuery, can_transition, ALLOWED_TRANSITIONS
)
from app.schemas.payments import PaymentMethod, PaymentCreate, PaymentRead
from app.schemas.reviews import ReviewCreate, ReviewRead

__all__ = [
    "ErrorDetail",
    "MessageResponse",
    "PropertyBase",
    "PropertyRead",
    "RoomTypeRead",
    "RoomRead",
    "RatePlanRead",
    "GuestBase",
    "GuestCreate",
    "GuestRead",
    "BookingStatus",
    "BookingCreate",
    "BookingStatusUpdate",
    "BookingRead",
    "AvailabilityQuery",
    "can_transition",
    "ALLOWED_TRANSITIONS",
    "PaymentMethod",
    "PaymentCreate",
    "PaymentRead",
    "ReviewCreate",
    "ReviewRead",
]
