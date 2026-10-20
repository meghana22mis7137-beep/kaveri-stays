from typing import Any, Optional
from fastapi import HTTPException, status

class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "status_code": status_code,
                "error": HTTPException(status_code=status_code).detail if status_code in (400, 404, 409, 422, 500) else "Error",
                "code": code,
                "message": message,
                "details": details
            }
        )
        self.code = code
        self.message = message
        self.details = details

class ConflictException(AppException):
    def __init__(self, code: str, message: str, details: Optional[Any] = None):
        super().__init__(status.HTTP_409_CONFLICT, code, message, details)

class NotFoundException(AppException):
    def __init__(self, code: str, message: str, details: Optional[Any] = None):
        super().__init__(status.HTTP_404_NOT_FOUND, code, message, details)

class ValidationException(AppException):
    def __init__(self, code: str, message: str, details: Optional[Any] = None):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, code, message, details)

class StateTransitionException(AppException):
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="INVALID_STATUS_TRANSITION",
            message=f"Cannot transition booking from '{current_status}' to '{target_status}'.",
            details={"current_status": current_status, "target_status": target_status}
        )

def explain(code: int) -> str:
    """Historical helper from course materials explaining HTTP codes."""
    return {
        200: "ok (or idempotent replay)",
        400: "bad request",
        404: "not found",
        409: "conflict (database unique, exclusion, or business constraint)",
        422: "unprocessable entity (invalid format, check constraint, or range error)",
        500: "internal server error (unhandled error or aborted transaction)"
    }.get(code, "unknown")

def translate_pg_error(exc: Exception) -> AppException:
    """
    Translates PostgreSQL errors (SQLSTATE codes) and constraint names into
    precise, documented HTTP AppExceptions matching the constraint inventory.
    """
    pgcode = getattr(exc, "pgcode", None)
    error_msg = str(exc)

    # 1. Unique constraint violation (23505 -> 409 Conflict)
    if pgcode == "23505" or "unique constraint" in error_msg.lower() or "unique index" in error_msg.lower():
        if "uq_guests_email_lower" in error_msg:
            return ConflictException(
                code="GUEST_EMAIL_EXISTS",
                message="A guest with this email address is already registered.",
                details={"constraint": "uq_guests_email_lower"}
            )
        if "reviews_booking_id_key" in error_msg:
            return ConflictException(
                code="REVIEW_ALREADY_EXISTS",
                message="A review has already been submitted for this booking.",
                details={"constraint": "reviews_booking_id_key"}
            )
        if "payments_idempotency_key_key" in error_msg:
            return ConflictException(
                code="IDEMPOTENCY_KEY_CONFLICT",
                message="A payment with this idempotency key already exists.",
                details={"constraint": "payments_idempotency_key_key"}
            )
        if "uq_property_room_number" in error_msg:
            return ConflictException(
                code="DUPLICATE_ROOM_NUMBER",
                message="A room with this number already exists at this property.",
                details={"constraint": "uq_property_room_number"}
            )
        return ConflictException(
            code="UNIQUE_VIOLATION",
            message="The record conflicts with an existing resource.",
            details={"raw_error": error_msg}
        )

    # 2. Exclusion constraint violation (23P01 -> 409 Conflict)
    if pgcode == "23P01" or "exclusion constraint" in error_msg.lower():
        if "no_overlapping_bookings" in error_msg:
            return ConflictException(
                code="ROOM_UNAVAILABLE",
                message="The requested room is unavailable for the selected dates because it conflicts with an existing reservation.",
                details={"constraint": "no_overlapping_bookings"}
            )
        if "no_overlapping_rates" in error_msg:
            return ConflictException(
                code="RATE_PLAN_OVERLAP",
                message="The rate plan validity period overlaps with an existing rate plan for this room type.",
                details={"constraint": "no_overlapping_rates"}
            )
        return ConflictException(
            code="EXCLUSION_VIOLATION",
            message="The requested date range conflicts with an existing entry.",
            details={"raw_error": error_msg}
        )

    # 3. Check constraint or trigger violations (23514 -> 422 or 409)
    if pgcode == "23514" or "check constraint" in error_msg.lower():
        # Review allowed only after checkout (mapped to 409 in constraint inventory)
        if "review allowed only after checkout" in error_msg or "trg_check_review_allowed" in error_msg:
            return ConflictException(
                code="REVIEW_NOT_PERMITTED",
                message="Reviews are only permitted after a booking has been checked out.",
                details={"constraint": "trg_check_review_allowed"}
            )
        if "guest count" in error_msg and "exceeds room maximum" in error_msg:
            return ValidationException(
                code="MAX_OCCUPANCY_EXCEEDED",
                message="The number of guests exceeds the maximum occupancy for this room type.",
                details={"constraint": "trg_check_occupancy"}
            )
        if "valid_stay" in error_msg:
            return ValidationException(
                code="INVALID_STAY_DATES",
                message="Stay check-out date must be strictly after check-in date.",
                details={"constraint": "valid_stay"}
            )
        if "bookings_guests_count_check" in error_msg:
            return ValidationException(
                code="INVALID_GUEST_COUNT",
                message="Number of guests must be at least 1.",
                details={"constraint": "bookings_guests_count_check"}
            )
        if "payments_amount_check" in error_msg:
            return ValidationException(
                code="INVALID_PAYMENT_AMOUNT",
                message="Payment amount must be greater than zero.",
                details={"constraint": "payments_amount_check"}
            )
        if "reviews_rating_check" in error_msg:
            return ValidationException(
                code="INVALID_RATING",
                message="Review rating must be between 1 and 5.",
                details={"constraint": "reviews_rating_check"}
            )
        return ValidationException(
            code="CHECK_VIOLATION",
            message="The submitted data violates a business rule constraint.",
            details={"raw_error": error_msg}
        )

    # 4. Foreign key violations (23503 -> 422 on insert, 409 on delete, 404 on payment booking)
    if pgcode == "23503" or "foreign key" in error_msg.lower():
        if "payments_booking_id_fkey" in error_msg:
            return NotFoundException(
                code="BOOKING_NOT_FOUND",
                message="Cannot record payment: the associated booking was not found.",
                details={"constraint": "payments_booking_id_fkey"}
            )
        if "delete" in error_msg.lower() or "is still referenced" in error_msg.lower():
            return ConflictException(
                code="FOREIGN_KEY_RESTRICTED",
                message="Cannot delete record because dependent records exist in another table.",
                details={"raw_error": error_msg}
            )
        return ValidationException(
            code="FOREIGN_KEY_NOT_FOUND",
            message="Referenced parent record does not exist.",
            details={"raw_error": error_msg}
        )

    # 5. Range or formatting errors (22000, 22P02 -> 422)
    if pgcode in ("22000", "22P02") or "range lower bound" in error_msg:
        return ValidationException(
            code="INVALID_INPUT_DATA",
            message="Data formatting or date range invalid.",
            details={"raw_error": error_msg}
        )

    # 6. Aborted transaction state (25P02 -> 500)
    if pgcode == "25P02":
        return AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TRANSACTION_ABORTED",
            message="Current database transaction was aborted.",
            details={"raw_error": error_msg}
        )

    # Fallback generic server error
    return AppException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="DATABASE_ERROR",
        message="An unexpected database error occurred.",
        details={"raw_error": error_msg}
    )
