from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

class GuestBase(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not clean or "@" not in clean:
            raise ValueError("Invalid email address")
        return clean

class GuestCreate(GuestBase):
    pass

class GuestRead(GuestBase):
    guest_id: int
