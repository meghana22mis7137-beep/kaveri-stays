from app.routers.properties import router as properties_router
from app.routers.guests import router as guests_router
from app.routers.bookings import router as bookings_router
from app.routers.payments import router as payments_router
from app.routers.reviews import router as reviews_router

__all__ = [
    "properties_router",
    "guests_router",
    "bookings_router",
    "payments_router",
    "reviews_router",
]
