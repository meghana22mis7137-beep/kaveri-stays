from typing import List
from fastapi import APIRouter, Path, Response, status
from app.models.repository import repo
from app.schemas.payments import PaymentCreate, PaymentRead

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("", response_model=PaymentRead, summary="Record a payment for a booking")
def create_payment(payment_in: PaymentCreate, response: Response):
    result = repo.create_payment(payment_in)
    if result.get("is_replay"):
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
    return result

@router.get("/{booking_id}", response_model=List[PaymentRead], summary="List all payments for a booking")
def list_payments(booking_id: int = Path(..., gt=0)):
    # Verify booking exists
    repo.get_booking(booking_id)
    return repo.list_payments(booking_id)
