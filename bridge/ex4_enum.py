from enum import Enum

class BookingStatus(str, Enum):
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    cancelled = "cancelled"
    no_show = "no_show"

ALLOWED = {
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
    return target in ALLOWED[current]

print(can_transition(BookingStatus.confirmed, BookingStatus.checked_in))
print(can_transition(BookingStatus.confirmed, BookingStatus.checked_out))
print(can_transition(BookingStatus.checked_out, BookingStatus.cancelled))