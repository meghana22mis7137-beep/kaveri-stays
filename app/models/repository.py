import threading
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from app.db import is_using_memory_fallback, get_db_connection
from app.errors import (
    ConflictException, NotFoundException, ValidationException,
    StateTransitionException, translate_pg_error
)
from app.schemas.bookings import (
    BookingStatus, BookingCreate, can_transition
)
from app.schemas.guests import GuestCreate
from app.schemas.payments import PaymentCreate, PaymentMethod
from app.schemas.reviews import ReviewCreate
from bridge.nights import nights

# Thread lock for in-memory operations to ensure thread safety
_lock = threading.Lock()

# Seed in-memory store matching 04_seed_small.sql exactly
class InMemoryStore:
    def __init__(self):
        self.reset()

    def reset(self):
        self.properties = [
            {"property_id": 1, "name": "Kaveri Riverside", "city": "Coorg", "star_rating": 4},
            {"property_id": 2, "name": "Kaveri Hilltop", "city": "Ooty", "star_rating": 5},
            {"property_id": 3, "name": "Kaveri Backwater", "city": "Alleppey", "star_rating": 4},
        ]
        self.room_types = [
            {"room_type_id": 1, "name": "Standard", "max_occupancy": 2},
            {"room_type_id": 2, "name": "Deluxe", "max_occupancy": 3},
            {"room_type_id": 3, "name": "Suite", "max_occupancy": 4},
        ]
        self.rooms = []
        room_id = 1
        for prop in self.properties:
            # 101-104 Standard, 201-204 Deluxe, 301-304 Suite
            for rnum, rtype_id in [
                ("101", 1), ("102", 1), ("103", 1), ("104", 1),
                ("201", 2), ("202", 2), ("203", 2), ("204", 2),
                ("301", 3), ("302", 3), ("303", 3), ("304", 3),
            ]:
                self.rooms.append({
                    "room_id": room_id,
                    "property_id": prop["property_id"],
                    "room_number": rnum,
                    "room_type_id": rtype_id,
                })
                room_id += 1

        self.guests = [
            {"guest_id": 1, "full_name": "Aarav Sharma", "email": "aarav.sharma@example.com", "phone": "+919876543210", "city": "Bengaluru"},
            {"guest_id": 2, "full_name": "Anita Desai", "email": "anita.desai@example.com", "phone": "+919123456789", "city": "Mumbai"},
            {"guest_id": 3, "full_name": "Ben Carter", "email": "ben.carter@example.org", "phone": "+447700900123", "city": "Bristol"},
            {"guest_id": 4, "full_name": "Chloe Dubois", "email": "chloe.dubois@example.com", "phone": "+33612345678", "city": "Lyon"},
            {"guest_id": 5, "full_name": "Elena Rossi", "email": "elena.rossi@example.com", "phone": "+393201234567", "city": "Milan"},
            {"guest_id": 6, "full_name": "Kavya Nair", "email": "kavya.nair@example.com", "phone": "+919456789012", "city": "Kochi"},
        ]

        self.rate_plans = [
            {"rate_plan_id": 1, "property_id": 1, "room_type_id": 1, "season_name": "Regular 2026", "valid_from": date(2026, 1, 5), "valid_to": date(2027, 1, 1), "nightly_rate": Decimal("3800.00")},
            {"rate_plan_id": 2, "property_id": 1, "room_type_id": 2, "season_name": "Regular 2026", "valid_from": date(2026, 1, 5), "valid_to": date(2027, 1, 1), "nightly_rate": Decimal("5320.00")},
            {"rate_plan_id": 3, "property_id": 1, "room_type_id": 3, "season_name": "Regular 2026", "valid_from": date(2026, 1, 5), "valid_to": date(2027, 1, 1), "nightly_rate": Decimal("7980.00")},
            {"rate_plan_id": 4, "property_id": 2, "room_type_id": 3, "season_name": "Regular 2026", "valid_from": date(2026, 1, 5), "valid_to": date(2027, 1, 1), "nightly_rate": Decimal("7980.00")},
        ]

        self.bookings = [
            {
                "booking_id": 1,
                "guest_id": 1,
                "room_id": 1, # Riverside 101
                "check_in": date(2026, 1, 10),
                "check_out": date(2026, 1, 14),
                "guests_count": 2,
                "nightly_rate": Decimal("3800.00"),
                "status": BookingStatus.checked_out,
                "created_at": "2026-01-01T10:00:00Z"
            },
            {
                "booking_id": 2,
                "guest_id": 2,
                "room_id": 5, # Riverside 201
                "check_in": date(2026, 12, 10),
                "check_out": date(2026, 12, 13),
                "guests_count": 2,
                "nightly_rate": Decimal("5320.00"),
                "status": BookingStatus.confirmed,
                "created_at": "2026-01-02T10:00:00Z"
            },
            {
                "booking_id": 3,
                "guest_id": 3,
                "room_id": 1, # Riverside 101
                "check_in": date(2026, 1, 14),
                "check_out": date(2026, 1, 16),
                "guests_count": 1,
                "nightly_rate": Decimal("3800.00"),
                "status": BookingStatus.checked_out,
                "created_at": "2026-01-03T10:00:00Z"
            },
            {
                "booking_id": 4,
                "guest_id": 4,
                "room_id": 21, # Hilltop 301
                "check_in": date(2026, 3, 1),
                "check_out": date(2026, 3, 5),
                "guests_count": 3,
                "nightly_rate": Decimal("7980.00"),
                "status": BookingStatus.cancelled,
                "created_at": "2026-01-04T10:00:00Z"
            },
        ]

        self.payments = [
            {"payment_id": 1, "booking_id": 1, "amount": Decimal("15200.00"), "method": "card", "paid_at": "2026-01-10T10:00:00Z", "idempotency_key": "seed-pay-1"},
            {"payment_id": 2, "booking_id": 2, "amount": Decimal("5000.00"), "method": "upi", "paid_at": "2026-12-10T10:00:00Z", "idempotency_key": "seed-pay-2"},
        ]

        self.reviews = [
            {"review_id": 1, "booking_id": 1, "rating": 5, "comments": "Peaceful stay by the river.", "reviewed_at": "2026-01-15T12:00:00Z"},
        ]
        
        self.next_guest_id = 7
        self.next_booking_id = 5
        self.next_payment_id = 3
        self.next_review_id = 2

store = InMemoryStore()

class Repository:
    # --- PROPERTIES & ROOMS ---
    def list_properties(self) -> List[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT property_id, name, city, star_rating FROM properties ORDER BY property_id;")
                        return cur.fetchall()
            except Exception as e:
                raise translate_pg_error(e)
        return store.properties

    def get_property(self, property_id: int) -> Dict[str, Any]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT property_id, name, city, star_rating FROM properties WHERE property_id = %s;", (property_id,))
                        row = cur.fetchone()
                        if not row:
                            raise NotFoundException("PROPERTY_NOT_FOUND", f"Property {property_id} not found.")
                        return row
            except Exception as e:
                if isinstance(e, NotFoundException): raise
                raise translate_pg_error(e)
        
        for p in store.properties:
            if p["property_id"] == property_id:
                return p
        raise NotFoundException("PROPERTY_NOT_FOUND", f"Property {property_id} not found.")

    def list_rooms(self, property_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        query = """
                            SELECT r.room_id, r.property_id, r.room_number, r.room_type_id,
                                   rt.name as room_type_name, rt.max_occupancy
                            FROM rooms r
                            JOIN room_types rt USING (room_type_id)
                        """
                        params = ()
                        if property_id is not None:
                            query += " WHERE r.property_id = %s"
                            params = (property_id,)
                        query += " ORDER BY r.room_id;"
                        cur.execute(query, params)
                        return cur.fetchall()
            except Exception as e:
                raise translate_pg_error(e)

        results = []
        for r in store.rooms:
            if property_id is None or r["property_id"] == property_id:
                rt = next(t for t in store.room_types if t["room_type_id"] == r["room_type_id"])
                results.append({
                    **r,
                    "room_type_name": rt["name"],
                    "max_occupancy": rt["max_occupancy"]
                })
        return results

    def get_room(self, room_id: int) -> Dict[str, Any]:
        rooms = self.list_rooms()
        for r in rooms:
            if r["room_id"] == room_id:
                return r
        raise NotFoundException("ROOM_NOT_FOUND", f"Room {room_id} not found.")

    # --- GUESTS ---
    def create_guest(self, guest_in: GuestCreate) -> Dict[str, Any]:
        clean_email = guest_in.email.strip().lower()
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO guests (full_name, email, phone, city)
                            VALUES (%s, %s, %s, %s)
                            RETURNING guest_id, full_name, email, phone, city;
                        """, (guest_in.full_name, clean_email, guest_in.phone, guest_in.city))
                        return cur.fetchone()
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            for g in store.guests:
                if g["email"].lower() == clean_email:
                    raise ConflictException(
                        code="GUEST_EMAIL_EXISTS",
                        message="A guest with this email address is already registered.",
                        details={"constraint": "uq_guests_email_lower"}
                    )
            new_guest = {
                "guest_id": store.next_guest_id,
                "full_name": guest_in.full_name,
                "email": clean_email,
                "phone": guest_in.phone,
                "city": guest_in.city,
            }
            store.next_guest_id += 1
            store.guests.append(new_guest)
            return new_guest

    def get_guest(self, guest_id: int) -> Dict[str, Any]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT guest_id, full_name, email, phone, city FROM guests WHERE guest_id = %s;", (guest_id,))
                        row = cur.fetchone()
                        if not row:
                            raise NotFoundException("GUEST_NOT_FOUND", f"Guest {guest_id} not found.")
                        return row
            except Exception as e:
                if isinstance(e, NotFoundException): raise
                raise translate_pg_error(e)

        for g in store.guests:
            if g["guest_id"] == guest_id:
                return g
        raise NotFoundException("GUEST_NOT_FOUND", f"Guest {guest_id} not found.")

    def list_guests(self) -> List[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT guest_id, full_name, email, phone, city FROM guests ORDER BY guest_id;")
                        return cur.fetchall()
            except Exception as e:
                raise translate_pg_error(e)
        return store.guests

    # --- BOOKINGS ---
    def check_availability(
        self,
        check_in: date,
        check_out: date,
        property_id: Optional[int] = None,
        guests_count: int = 1
    ) -> List[Dict[str, Any]]:
        nights_count = nights(check_in, check_out)
        all_rooms = self.list_rooms(property_id)
        available = []

        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        for r in all_rooms:
                            if r["max_occupancy"] < guests_count:
                                continue
                            cur.execute("""
                                SELECT COUNT(*) as conflict_count
                                FROM bookings
                                WHERE room_id = %s
                                  AND status NOT IN ('cancelled', 'no_show')
                                  AND stay && daterange(%s, %s, '[)');
                            """, (r["room_id"], check_in, check_out))
                            res = cur.fetchone()
                            if res["conflict_count"] == 0:
                                available.append(r)
                return available
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            for r in all_rooms:
                if r["max_occupancy"] < guests_count:
                    continue
                # Check overlap in memory
                conflict = False
                for b in store.bookings:
                    if b["room_id"] == r["room_id"] and b["status"] not in (BookingStatus.cancelled, BookingStatus.no_show):
                        # Overlap check for [b_in, b_out) and [check_in, check_out)
                        if max(b["check_in"], check_in) < min(b["check_out"], check_out):
                            conflict = True
                            break
                if not conflict:
                    available.append(r)
        return available

    def create_booking(self, booking_in: BookingCreate) -> Dict[str, Any]:
        num_nights = nights(booking_in.check_in, booking_in.check_out)
        room = self.get_room(booking_in.room_id)
        guest = self.get_guest(booking_in.guest_id)

        # Check occupancy constraint (Rule 3)
        if booking_in.guests_count > room["max_occupancy"]:
            raise ValidationException(
                code="MAX_OCCUPANCY_EXCEEDED",
                message=f"Guest count {booking_in.guests_count} exceeds room maximum {room['max_occupancy']}.",
                details={"constraint": "trg_check_occupancy", "room_id": room["room_id"], "max_occupancy": room["max_occupancy"]}
            )

        nightly_rate = booking_in.nightly_rate
        if nightly_rate is None:
            nightly_rate = Decimal("3800.00") # default rate

        total_amount = nightly_rate * num_nights

        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Insert booking atomically
                        cur.execute("""
                            INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate, status)
                            VALUES (%s, %s, daterange(%s, %s, '[)'), %s, %s, 'confirmed')
                            RETURNING booking_id, guest_id, room_id, lower(stay) as check_in, upper(stay) as check_out,
                                      guests_count, nightly_rate, status, created_at;
                        """, (booking_in.guest_id, booking_in.room_id, booking_in.check_in, booking_in.check_out,
                              booking_in.guests_count, nightly_rate))
                        new_b = cur.fetchone()
                        booking_id = new_b["booking_id"]

                        # If deposit is provided, execute atomic payment within same transaction
                        deposit_payment = None
                        if booking_in.deposit_amount is not None:
                            cur.execute("""
                                INSERT INTO payments (booking_id, amount, method, idempotency_key)
                                VALUES (%s, %s, %s, %s)
                                RETURNING payment_id, booking_id, amount, method, paid_at, idempotency_key;
                            """, (booking_id, booking_in.deposit_amount, booking_in.deposit_method or "upi", booking_in.idempotency_key))
                            deposit_payment = cur.fetchone()

                        return self._format_booking_read(new_b, guest=guest, room=room)
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            # Overlap check for memory store (Rule 4 / 23P01)
            for b in store.bookings:
                if b["room_id"] == booking_in.room_id and b["status"] not in (BookingStatus.cancelled, BookingStatus.no_show):
                    if max(b["check_in"], booking_in.check_in) < min(b["check_out"], booking_in.check_out):
                        raise ConflictException(
                            code="ROOM_UNAVAILABLE",
                            message="The requested room is unavailable for the selected dates because it conflicts with an existing reservation.",
                            details={
                                "constraint": "no_overlapping_bookings",
                                "room_id": booking_in.room_id,
                                "conflicting_booking_id": b["booking_id"],
                                "conflicting_dates": [str(b["check_in"]), str(b["check_out"])]
                            }
                        )

            # Atomic transaction creation
            new_booking_id = store.next_booking_id
            now_iso = datetime.utcnow().isoformat() + "Z"
            
            # Check deposit payment validity before modifying state
            if booking_in.deposit_amount is not None:
                if booking_in.deposit_amount <= 0:
                    raise ValidationException(
                        code="INVALID_PAYMENT_AMOUNT",
                        message="Payment amount must be greater than zero.",
                        details={"constraint": "payments_amount_check"}
                    )
                if booking_in.idempotency_key:
                    for p in store.payments:
                        if p.get("idempotency_key") == booking_in.idempotency_key:
                            raise ConflictException(
                                code="IDEMPOTENCY_KEY_CONFLICT",
                                message="A payment with this idempotency key already exists.",
                                details={"constraint": "payments_idempotency_key_key"}
                            )

            booking_record = {
                "booking_id": new_booking_id,
                "guest_id": booking_in.guest_id,
                "room_id": booking_in.room_id,
                "check_in": booking_in.check_in,
                "check_out": booking_in.check_out,
                "guests_count": booking_in.guests_count,
                "nightly_rate": nightly_rate,
                "status": BookingStatus.confirmed,
                "created_at": now_iso
            }
            store.bookings.append(booking_record)
            store.next_booking_id += 1

            if booking_in.deposit_amount is not None:
                pay_record = {
                    "payment_id": store.next_payment_id,
                    "booking_id": new_booking_id,
                    "amount": booking_in.deposit_amount,
                    "method": booking_in.deposit_method or "upi",
                    "paid_at": now_iso,
                    "idempotency_key": booking_in.idempotency_key
                }
                store.payments.append(pay_record)
                store.next_payment_id += 1

            return self._format_booking_read(booking_record, guest=guest, room=room)

    def get_booking(self, booking_id: int) -> Dict[str, Any]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT booking_id, guest_id, room_id, lower(stay) as check_in, upper(stay) as check_out,
                                   guests_count, nightly_rate, status, created_at
                            FROM bookings
                            WHERE booking_id = %s;
                        """, (booking_id,))
                        b = cur.fetchone()
                        if not b:
                            raise NotFoundException("BOOKING_NOT_FOUND", f"Booking {booking_id} not found.")
                        guest = self.get_guest(b["guest_id"])
                        room = self.get_room(b["room_id"])
                        return self._format_booking_read(b, guest=guest, room=room)
            except Exception as e:
                if isinstance(e, NotFoundException): raise
                raise translate_pg_error(e)

        for b in store.bookings:
            if b["booking_id"] == booking_id:
                guest = self.get_guest(b["guest_id"])
                room = self.get_room(b["room_id"])
                return self._format_booking_read(b, guest=guest, room=room)
        raise NotFoundException("BOOKING_NOT_FOUND", f"Booking {booking_id} not found.")

    def list_bookings(
        self,
        guest_id: Optional[int] = None,
        room_id: Optional[int] = None,
        status: Optional[BookingStatus] = None
    ) -> List[Dict[str, Any]]:
        all_bookings = []
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        query = """
                            SELECT booking_id, guest_id, room_id, lower(stay) as check_in, upper(stay) as check_out,
                                   guests_count, nightly_rate, status, created_at
                            FROM bookings
                            WHERE 1=1
                        """
                        params = []
                        if guest_id:
                            query += " AND guest_id = %s"
                            params.append(guest_id)
                        if room_id:
                            query += " AND room_id = %s"
                            params.append(room_id)
                        if status:
                            query += " AND status = %s"
                            params.append(status.value)
                        query += " ORDER BY booking_id;"
                        cur.execute(query, tuple(params))
                        rows = cur.fetchall()
                        for r in rows:
                            all_bookings.append(self._format_booking_read(r))
                return all_bookings
            except Exception as e:
                raise translate_pg_error(e)

        for b in store.bookings:
            if guest_id and b["guest_id"] != guest_id: continue
            if room_id and b["room_id"] != room_id: continue
            if status and b["status"] != status: continue
            all_bookings.append(self._format_booking_read(b))
        return all_bookings

    def update_booking_status(self, booking_id: int, target_status: BookingStatus) -> Dict[str, Any]:
        """
        Transitions booking status validating state machine rules from bridge/ex4_enum.py
        """
        current_booking = self.get_booking(booking_id)
        current_status = BookingStatus(current_booking["status"])

        if current_status == target_status:
            return current_booking

        if not can_transition(current_status, target_status):
            raise StateTransitionException(current_status.value, target_status.value)

        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE bookings
                            SET status = %s
                            WHERE booking_id = %s
                            RETURNING booking_id, guest_id, room_id, lower(stay) as check_in, upper(stay) as check_out,
                                      guests_count, nightly_rate, status, created_at;
                        """, (target_status.value, booking_id))
                        updated = cur.fetchone()
                        return self._format_booking_read(updated)
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            for b in store.bookings:
                if b["booking_id"] == booking_id:
                    b["status"] = target_status
                    return self._format_booking_read(b)
        raise NotFoundException("BOOKING_NOT_FOUND", f"Booking {booking_id} not found.")

    # --- PAYMENTS ---
    def create_payment(self, payment_in: PaymentCreate) -> Dict[str, Any]:
        if payment_in.amount <= 0:
            raise ValidationException(
                code="INVALID_PAYMENT_AMOUNT",
                message="Payment amount must be greater than zero.",
                details={"constraint": "payments_amount_check"}
            )

        # Check booking existence
        self.get_booking(payment_in.booking_id)

        # Idempotency check: if replaying with identical idempotency key, return existing payment (HTTP 200)
        if payment_in.idempotency_key:
            existing = self.find_payment_by_idempotency_key(payment_in.idempotency_key)
            if existing:
                return {**existing, "is_replay": True}

        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO payments (booking_id, amount, method, idempotency_key)
                            VALUES (%s, %s, %s, %s)
                            RETURNING payment_id, booking_id, amount, method, paid_at, idempotency_key;
                        """, (payment_in.booking_id, payment_in.amount, payment_in.method.value, payment_in.idempotency_key))
                        return cur.fetchone()
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            now_iso = datetime.utcnow().isoformat() + "Z"
            pay_record = {
                "payment_id": store.next_payment_id,
                "booking_id": payment_in.booking_id,
                "amount": payment_in.amount,
                "method": payment_in.method.value,
                "paid_at": now_iso,
                "idempotency_key": payment_in.idempotency_key,
                "is_replay": False
            }
            store.payments.append(pay_record)
            store.next_payment_id += 1
            return pay_record

    def find_payment_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT payment_id, booking_id, amount, method, paid_at, idempotency_key
                            FROM payments
                            WHERE idempotency_key = %s;
                        """, (idempotency_key,))
                        return cur.fetchone()
            except Exception as e:
                raise translate_pg_error(e)

        for p in store.payments:
            if p.get("idempotency_key") == idempotency_key:
                return p
        return None

    def list_payments(self, booking_id: int) -> List[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT payment_id, booking_id, amount, method, paid_at, idempotency_key
                            FROM payments
                            WHERE booking_id = %s
                            ORDER BY payment_id;
                        """, (booking_id,))
                        return cur.fetchall()
            except Exception as e:
                raise translate_pg_error(e)

        return [p for p in store.payments if p["booking_id"] == booking_id]

    # --- REVIEWS ---
    def create_review(self, review_in: ReviewCreate) -> Dict[str, Any]:
        # Rating check 1 to 5
        if not (1 <= review_in.rating <= 5):
            raise ValidationException(
                code="INVALID_RATING",
                message="Review rating must be between 1 and 5.",
                details={"constraint": "reviews_rating_check"}
            )

        booking = self.get_booking(review_in.booking_id)

        # Rule 9 / Trigger: Review allowed ONLY after checkout (mapped to 409 in constraint inventory)
        if booking["status"] != BookingStatus.checked_out.value:
            raise ConflictException(
                code="REVIEW_NOT_PERMITTED",
                message=f"Review allowed only after checkout (current booking status is '{booking['status']}').",
                details={"constraint": "trg_check_review_allowed"}
            )

        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO reviews (booking_id, rating, comments)
                            VALUES (%s, %s, %s)
                            RETURNING review_id, booking_id, rating, comments, reviewed_at;
                        """, (review_in.booking_id, review_in.rating, review_in.comments))
                        return cur.fetchone()
            except Exception as e:
                raise translate_pg_error(e)

        with _lock:
            # Single review per booking constraint (Rule 9 / 23505)
            for r in store.reviews:
                if r["booking_id"] == review_in.booking_id:
                    raise ConflictException(
                        code="REVIEW_ALREADY_EXISTS",
                        message="A review has already been submitted for this booking.",
                        details={"constraint": "reviews_booking_id_key"}
                    )

            now_iso = datetime.utcnow().isoformat() + "Z"
            rev_record = {
                "review_id": store.next_review_id,
                "booking_id": review_in.booking_id,
                "rating": review_in.rating,
                "comments": review_in.comments,
                "reviewed_at": now_iso
            }
            store.reviews.append(rev_record)
            store.next_review_id += 1
            return rev_record

    def list_reviews(self) -> List[Dict[str, Any]]:
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT review_id, booking_id, rating, comments, reviewed_at
                            FROM reviews
                            ORDER BY review_id DESC;
                        """, ())
                        return cur.fetchall()
            except Exception as e:
                raise translate_pg_error(e)

        return list(reversed(store.reviews))

    # Helper formatter
    def _format_booking_read(self, b: Dict[str, Any], guest=None, room=None) -> Dict[str, Any]:
        ch_in = b["check_in"]
        ch_out = b["check_out"]
        n_nights = nights(ch_in, ch_out)
        rate = Decimal(str(b["nightly_rate"]))
        total = rate * n_nights
        
        # Calculate payments total
        if not is_using_memory_fallback():
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COALESCE(SUM(amount), 0) as paid FROM payments WHERE booking_id = %s;", (b["booking_id"],))
                        row = cur.fetchone()
                        paid_amount = Decimal(str(row["paid"])) if row else Decimal("0.00")
            except Exception:
                paid_amount = Decimal("0.00")
        else:
            pays = [p for p in store.payments if p["booking_id"] == b["booking_id"]]
            paid_amount = sum((p["amount"] for p in pays), Decimal("0.00"))
        
        if guest is None:
            try:
                guest = self.get_guest(b["guest_id"])
            except Exception:
                guest = None
        if room is None:
            try:
                room = self.get_room(b["room_id"])
            except Exception:
                room = None
        
        return {
            "booking_id": b["booking_id"],
            "guest_id": b["guest_id"],
            "room_id": b["room_id"],
            "check_in": ch_in,
            "check_out": ch_out,
            "stay_str": f"[{ch_in}, {ch_out})",
            "nights": n_nights,
            "guests_count": b["guests_count"],
            "nightly_rate": rate,
            "total_amount": total,
            "status": b["status"] if isinstance(b["status"], str) else b["status"].value,
            "created_at": str(b["created_at"]),
            "guest": guest,
            "room": room,
            "payments_total": paid_amount,
            "is_fully_paid": paid_amount >= total
        }

repo = Repository()
