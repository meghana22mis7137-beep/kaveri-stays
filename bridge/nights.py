from datetime import date

def nights(check_in: date, check_out: date) -> int:
    n = (check_out - check_in).days
    if n <= 0:
        raise ValueError("check_out must be after check_in")
    return n