-- =========================================================
-- Kaveri Stays: original schema (rules 1 to 10)
-- =========================================================

DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS rate_plans CASCADE;
DROP TABLE IF EXISTS guests CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS room_types CASCADE;
DROP TABLE IF EXISTS properties CASCADE;
DROP FUNCTION IF EXISTS check_occupancy() CASCADE;
DROP FUNCTION IF EXISTS check_review_allowed() CASCADE;
DROP TYPE IF EXISTS booking_status CASCADE;
DROP TYPE IF EXISTS payment_method_type CASCADE;

-- Needed for the "no overlap" constraints (rules 4 and 6)
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE booking_status AS ENUM
    ('confirmed', 'checked_in', 'checked_out', 'cancelled', 'no_show');   -- rule 7

CREATE TYPE payment_method_type AS ENUM
    ('card', 'upi', 'bank_transfer', 'cash');                             -- rule 8

-- Rule 1: three properties, more may open later
CREATE TABLE properties (
    property_id  SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    city         VARCHAR(100) NOT NULL,
    star_rating  SMALLINT NOT NULL CHECK (star_rating BETWEEN 1 AND 5)
);

-- Rule 3: each room type has a maximum occupancy
CREATE TABLE room_types (
    room_type_id   SERIAL PRIMARY KEY,
    name           VARCHAR(50) NOT NULL UNIQUE,
    max_occupancy  SMALLINT NOT NULL CHECK (max_occupancy > 0)
);

-- Rule 2: room number unique within a property, repeatable across properties
CREATE TABLE rooms (
    room_id       SERIAL PRIMARY KEY,
    property_id   INT NOT NULL REFERENCES properties(property_id) ON DELETE RESTRICT,
    room_number   VARCHAR(10) NOT NULL,
    room_type_id  INT NOT NULL REFERENCES room_types(room_type_id) ON DELETE RESTRICT,
    CONSTRAINT uq_property_room_number UNIQUE (property_id, room_number)
);

-- Rule 10: guests identified by email, case-insensitive
CREATE TABLE guests (
    guest_id   SERIAL PRIMARY KEY,
    full_name  VARCHAR(150) NOT NULL,
    email      VARCHAR(255) NOT NULL,
    phone      VARCHAR(30),
    city       VARCHAR(100)
);
CREATE UNIQUE INDEX uq_guests_email_lower ON guests (LOWER(TRIM(email)));

-- Rule 6: nightly rates by property, room type and season; no overlapping periods
CREATE TABLE rate_plans (
    rate_plan_id  SERIAL PRIMARY KEY,
    property_id   INT NOT NULL REFERENCES properties(property_id) ON DELETE RESTRICT,
    room_type_id  INT NOT NULL REFERENCES room_types(room_type_id) ON DELETE RESTRICT,
    season_name   VARCHAR(50) NOT NULL,
    valid         DATERANGE NOT NULL,
    nightly_rate  NUMERIC(10,2) NOT NULL CHECK (nightly_rate > 0),
    CONSTRAINT no_overlapping_rates EXCLUDE USING gist (
        property_id WITH =,
        room_type_id WITH =,
        valid WITH &&
    )
);

-- Rules 4, 5, 7: bookings
-- stay is a [) range: check-in day counts, check-out day does not,
-- so same-day turnover is allowed (rule 5)
CREATE TABLE bookings (
    booking_id    SERIAL PRIMARY KEY,
    guest_id      INT NOT NULL REFERENCES guests(guest_id) ON DELETE RESTRICT,
    room_id       INT NOT NULL REFERENCES rooms(room_id) ON DELETE RESTRICT,
    stay          DATERANGE NOT NULL,
    guests_count  SMALLINT NOT NULL CHECK (guests_count > 0),
    nightly_rate  NUMERIC(10,2) NOT NULL CHECK (nightly_rate > 0),
    status        booking_status NOT NULL DEFAULT 'confirmed',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_stay CHECK (NOT isempty(stay) AND lower(stay) < upper(stay)),
    -- rule 4 + 2.5: no overlap, but cancelled / no-show bookings do not block the room
    CONSTRAINT no_overlapping_bookings EXCLUDE USING gist (
        room_id WITH =,
        stay WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'))
);

-- Rule 3 (task 2.7): guest count may not exceed the room type's maximum.
-- It spans three tables, so a CHECK cannot express it. A trigger can, and
-- it fires for every writer (API, psql, scripts).
CREATE FUNCTION check_occupancy() RETURNS trigger AS $$
DECLARE
    v_max SMALLINT;
BEGIN
    SELECT rt.max_occupancy INTO v_max
    FROM rooms r
    JOIN room_types rt ON rt.room_type_id = r.room_type_id
    WHERE r.room_id = NEW.room_id;

    IF NEW.guests_count > v_max THEN
        RAISE EXCEPTION 'guest count % exceeds room maximum %', NEW.guests_count, v_max
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_occupancy
BEFORE INSERT OR UPDATE OF guests_count, room_id ON bookings
FOR EACH ROW EXECUTE FUNCTION check_occupancy();

-- Rule 8: one booking, several payments
CREATE TABLE payments (
    payment_id       SERIAL PRIMARY KEY,
    booking_id       INT NOT NULL REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    amount           NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    method           payment_method_type NOT NULL,
    paid_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    idempotency_key  VARCHAR(100) UNIQUE   -- lets the API detect a retried payment later
);

-- Rule 9: one review per booking, rating 1 to 5, only after checkout
CREATE TABLE reviews (
    review_id    SERIAL PRIMARY KEY,
    booking_id   INT NOT NULL UNIQUE REFERENCES bookings(booking_id) ON DELETE CASCADE,
    rating       SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments     TEXT,
    reviewed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE FUNCTION check_review_allowed() RETURNS trigger AS $$
DECLARE
    v_status booking_status;
BEGIN
    SELECT status INTO v_status FROM bookings WHERE booking_id = NEW.booking_id;
    IF v_status IS DISTINCT FROM 'checked_out' THEN
        RAISE EXCEPTION 'review allowed only after checkout (booking status is %)', v_status
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_review_allowed
BEFORE INSERT ON reviews
FOR EACH ROW EXECUTE FUNCTION check_review_allowed();