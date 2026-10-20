import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.models.repository import store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_database_state():
    """Reset store state before each test run."""
    store.reset()

def test_system_endpoints():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "online"

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_properties_and_rooms():
    r = client.get("/properties")
    assert r.status_code == 200
    props = r.json()
    assert len(props) == 3
    assert props[0]["name"] == "Kaveri Riverside"

    r = client.get("/properties/1")
    assert r.status_code == 200
    p1 = r.json()
    assert len(p1["rooms"]) == 12

    # Non-existent property
    r = client.get("/properties/999")
    assert r.status_code == 404

def test_guest_registration_and_case_insensitive_unique():
    # 1. Register new guest
    payload = {
        "full_name": "Test User",
        "email": "NewGuest@example.com",
        "phone": "+919999999999",
        "city": "Hyderabad"
    }
    r = client.post("/guests", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "newguest@example.com" # normalized lower

    # 2. Duplicate registration attempt with different casing (Rule 10, SQLSTATE 23505 -> 409)
    r2 = client.post("/guests", json=payload)
    assert r2.status_code == 409
    err = r2.json()
    assert err["code"] == "GUEST_EMAIL_EXISTS"

def test_availability_search():
    # Check availability for Room 101 dates where it is free
    r = client.get("/bookings/availability", params={
        "check_in": "2026-06-01",
        "check_out": "2026-06-05",
        "property_id": 1,
        "guests_count": 2
    })
    assert r.status_code == 200
    available_rooms = r.json()
    assert len(available_rooms) > 0

    # Invalid dates (checkout before checkin)
    r_bad = client.get("/bookings/availability", params={
        "check_in": "2026-06-10",
        "check_out": "2026-06-05"
    })
    assert r_bad.status_code == 422

def test_booking_happy_path_with_atomic_deposit():
    # Create booking with atomic deposit (Rule 8 / Task 6)
    booking_payload = {
        "guest_id": 1,
        "room_id": 2, # Riverside 102
        "check_in": "2026-07-01",
        "check_out": "2026-07-04",
        "guests_count": 2,
        "nightly_rate": "3800.00",
        "deposit_amount": "3800.00",
        "deposit_method": "upi",
        "idempotency_key": "dep-atom-1"
    }
    r = client.post("/bookings", json=booking_payload)
    assert r.status_code == 201
    b = r.json()
    assert b["nights"] == 3
    assert b["total_amount"] == "11400.00"
    assert b["payments_total"] == "3800.00"
    assert b["status"] == "confirmed"

def test_booking_exclusion_constraint_overlap():
    # Room 1 (101) has booking from 2026-01-10 to 2026-01-14
    # Attempt overlapping booking 2026-01-12 to 2026-01-15 (5.1 attack, SQLSTATE 23P01 -> 409)
    overlap_payload = {
        "guest_id": 5,
        "room_id": 1,
        "check_in": "2026-01-12",
        "check_out": "2026-01-15",
        "guests_count": 2,
        "nightly_rate": "3800.00"
    }
    r = client.post("/bookings", json=overlap_payload)
    assert r.status_code == 409
    err = r.json()
    assert err["code"] == "ROOM_UNAVAILABLE"
    assert "no_overlapping_bookings" in str(err["details"])

def test_same_day_turnover_allowed():
    # Booking 1 ends 2026-01-14. Booking starting 2026-01-14 to 2026-01-17 on Room 2
    # Create first booking
    r1 = client.post("/bookings", json={
        "guest_id": 1,
        "room_id": 3,
        "check_in": "2026-08-01",
        "check_out": "2026-08-05",
        "guests_count": 2
    })
    assert r1.status_code == 201

    # Same-day turnover: starts exactly on 2026-08-05 (Rule 5)
    r2 = client.post("/bookings", json={
        "guest_id": 2,
        "room_id": 3,
        "check_in": "2026-08-05",
        "check_out": "2026-08-08",
        "guests_count": 2
    })
    assert r2.status_code == 201

def test_booking_max_occupancy_violation():
    # Room 1 is Standard (max occupancy 2). Attempt 4 guests (5.4 attack, 23514 -> 422)
    overcap_payload = {
        "guest_id": 1,
        "room_id": 1,
        "check_in": "2026-09-01",
        "check_out": "2026-09-04",
        "guests_count": 4, # Exceeds 2
        "nightly_rate": "3800.00"
    }
    r = client.post("/bookings", json=overcap_payload)
    assert r.status_code == 422
    err = r.json()
    assert err["code"] == "MAX_OCCUPANCY_EXCEEDED"

def test_booking_status_transitions():
    # Booking 2 is confirmed
    # 1. confirmed -> checked_in (Valid)
    r = client.patch("/bookings/2/status", json={"status": "checked_in"})
    assert r.status_code == 200
    assert r.json()["status"] == "checked_in"

    # 2. checked_in -> checked_out (Valid)
    r = client.patch("/bookings/2/status", json={"status": "checked_out"})
    assert r.status_code == 200
    assert r.json()["status"] == "checked_out"

    # 3. checked_out -> cancelled (Invalid transition per bridge/ex4_enum.py)
    r_bad = client.patch("/bookings/2/status", json={"status": "cancelled"})
    assert r_bad.status_code == 422
    err = r_bad.json()
    assert err["code"] == "INVALID_STATUS_TRANSITION"

def test_payment_idempotency_and_amount_check():
    # 1. Fresh payment
    pay_payload = {
        "booking_id": 2,
        "amount": "1000.00",
        "method": "upi",
        "idempotency_key": "pay-unique-123"
    }
    r = client.post("/payments", json=pay_payload)
    assert r.status_code == 201

    # 2. Idempotent replay with same key: returns HTTP 200 with original payment
    r_replay = client.post("/payments", json=pay_payload)
    assert r_replay.status_code == 200
    assert r_replay.json()["idempotency_key"] == "pay-unique-123"

    # 3. Invalid negative amount (5.10 attack, 23514 -> 422)
    r_neg = client.post("/payments", json={
        "booking_id": 2,
        "amount": "-50.00",
        "method": "card"
    })
    assert r_neg.status_code == 422

def test_review_business_rules():
    # Booking 2 is confirmed (not checked out) -> review must fail (5.13 attack, 409 Conflict)
    r_premature = client.post("/reviews", json={
        "booking_id": 2,
        "rating": 5,
        "comments": "Too early!"
    })
    assert r_premature.status_code == 409
    assert r_premature.json()["code"] == "REVIEW_NOT_PERMITTED"

    # Booking 1 already has a review -> second review must fail (5.12 attack, 409 Conflict)
    r_duplicate = client.post("/reviews", json={
        "booking_id": 1,
        "rating": 4,
        "comments": "Second review"
    })
    assert r_duplicate.status_code == 409
    assert r_duplicate.json()["code"] == "REVIEW_ALREADY_EXISTS"

    # Booking 3 is checked_out and has no review -> valid review (201 Created)
    r_valid = client.post("/reviews", json={
        "booking_id": 3,
        "rating": 5,
        "comments": "Wonderful experience."
    })
    assert r_valid.status_code == 201
    assert r_valid.json()["rating"] == 5

    # Invalid rating > 5 (5.11 attack, 23514 -> 422)
    r_bad_rating = client.post("/reviews", json={
        "booking_id": 3,
        "rating": 9
    })
    assert r_bad_rating.status_code == 422
