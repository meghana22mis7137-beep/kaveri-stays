from datetime import date
from decimal import Decimal

def nights(check_in: date, check_out: date) -> int:
    return (check_out - check_in).days

def total(rate: Decimal, n: int) -> Decimal:
    return rate * n

def first_or_none(items: list[str]) -> str | None:
    return items[0] if items else None

print(nights(date(2026, 3, 1), date(2026, 3, 6)))
print(total(Decimal("2500.50"), 3))
print(first_or_none([]))