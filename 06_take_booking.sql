\set VERBOSITY verbose
SELECT r.room_id AS r104 FROM rooms r JOIN properties p USING (property_id)
  WHERE p.name = 'Kaveri Riverside' AND r.room_number = '104' \gset

\echo === SUCCESS: booking and deposit commit together ===
BEGIN;
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r104, daterange('2026-10-10','2026-10-13'), 2, 3800);
INSERT INTO payments (booking_id, amount, method)
VALUES (currval('bookings_booking_id_seq'), 3800, 'upi');
COMMIT;

SELECT b.booking_id, b.stay, p.amount
FROM bookings b JOIN payments p USING (booking_id)
WHERE b.stay = daterange('2026-10-10','2026-10-13');

\echo === FAILURE HALFWAY: booking inserts, payment fails, everything rolls back ===
BEGIN;
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (6, :r104, daterange('2026-11-10','2026-11-13'), 2, 3800);
INSERT INTO payments (booking_id, amount, method)
VALUES (currval('bookings_booking_id_seq'), -1, 'upi');
ROLLBACK;

\echo === Proof: no booking exists for the failed attempt (expect 0) ===
SELECT count(*) AS bookings_left_behind
FROM bookings WHERE stay = daterange('2026-11-10','2026-11-13');