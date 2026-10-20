from datetime import date
from pydantic import BaseModel, model_validator, Field, ValidationError

class BookingCreate(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(gt=0)

    @model_validator(mode="after")
    def check_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self

print(BookingCreate(check_in="2026-03-01", check_out="2026-03-05", guests=2))

try:
    BookingCreate(check_in="2026-03-05", check_out="2026-03-01", guests=2)
except ValidationError as e:
    print(e)