from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field

class PaymentMethod(str, Enum):
    card = "card"
    upi = "upi"
    bank_transfer = "bank_transfer"
    cash = "cash"

class PaymentCreate(BaseModel):
    booking_id: int
    amount: Decimal = Field(gt=0, description="Payment amount must be greater than zero")
    method: PaymentMethod
    idempotency_key: Optional[str] = Field(default=None, max_length=100)

class PaymentRead(BaseModel):
    payment_id: int
    booking_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: Union[datetime, str]
    idempotency_key: Optional[str] = None
