from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Path, Query, status
from app.models.repository import repo
from app.schemas.bookings import (
    BookingCreate, BookingRead, BookingStatus, BookingStatusUpdate
)
from app.schemas.properties import RoomRead

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED, summary="Create a new booking")
def create_booking(booking_in: BookingCreate):
    return repo.create_booking(booking_in)

@router.get("/availability", response_model=List[RoomRead], summary="Search available rooms for dates")
def check_availability(
    check_in: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    check_out: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    property_id: Optional[int] = Query(None, description="Optional property filter"),
    guests_count: int = Query(1, ge=1, description="Required guest capacity")
):
    if check_out <= check_in:
        from app.errors import ValidationException
        raise ValidationException(
            code="INVALID_STAY_DATES",
            message="Check-out date must be strictly after check-in date."
        )
    return repo.check_availability(
        check_in=check_in,
        check_out=check_out,
        property_id=property_id,
        guests_count=guests_count
    )

@router.get("", response_model=List[BookingRead], summary="List bookings")
def list_bookings(
    guest_id: Optional[int] = Query(None),
    room_id: Optional[int] = Query(None),
    status: Optional[BookingStatus] = Query(None)
):
    return repo.list_bookings(guest_id=guest_id, room_id=room_id, status=status)

@router.get("/{booking_id}", response_model=BookingRead, summary="Get booking details by ID")
def get_booking(booking_id: int = Path(..., gt=0)):
    return repo.get_booking(booking_id)

@router.patch("/{booking_id}/status", response_model=BookingRead, summary="Update booking lifecycle status")
def update_status(
    booking_id: int = Path(..., gt=0),
    update_in: BookingStatusUpdate = ...
):
    return repo.update_booking_status(booking_id, update_in.status)
