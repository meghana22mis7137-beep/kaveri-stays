\set VERBOSITY verbose
\echo
\echo ===== Looking up some room ids =====
SELECT r.room_id AS r101 FROM rooms r JOIN properties p USING (property_id)
  WHERE p.name = 'Kaveri Riverside' AND r.room_number = '101' \gset
SELECT r.room_id AS r102 FROM rooms r JOIN properties p USING (property_id)
  WHERE p.name = 'Kaveri Riverside' AND r.room_number = '102' \gset
SELECT r.room_id AS r103 FROM rooms r JOIN properties p USING (property_id)
  WHERE p.name = 'Kaveri Riverside' AND r.room_number = '103' \gset
SELECT r.room_id AS h301 FROM rooms r JOIN properties p USING (property_id)
  WHERE p.name = 'Kaveri Hilltop' AND r.room_number = '301' \gset

\echo
\echo ===== ATTACKS: every one of these must fail =====

\echo 5.1 overlap with an existing booking
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r101, daterange('2026-01-12','2026-01-15','[)'), 2, 3800);

\echo 5.2 check-out before check-in
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r102, daterange('2026-05-05','2026-05-01','[)'), 2, 3800);

\echo 5.3 zero nights
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r102, daterange('2026-05-01','2026-05-01','[)'), 2, 3800);

\echo 5.4 four guests in a Standard room (max 2)
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r102, daterange('2026-05-01','2026-05-04','[)'), 4, 3800);

\echo 5.5 second room 101 at the same property
INSERT INTO rooms (property_id, room_number, room_type_id) VALUES (1, '101', 1);

\echo 5.6 status maybe
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate, status)
VALUES (5, :r102, daterange('2026-05-01','2026-05-04','[)'), 2, 3800, 'maybe');

\echo 5.7 guest that does not exist
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (9999, :r102, daterange('2026-05-01','2026-05-04','[)'), 2, 3800);

\echo 5.8 same email, different capitalisation
INSERT INTO guests (full_name, email) VALUES ('Fake Aarav', 'AARAV.SHARMA@EXAMPLE.COM');

\echo 5.9 delete a property that still has rooms
DELETE FROM properties WHERE name = 'Kaveri Riverside';

\echo 5.10 negative nightly rate
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r102, daterange('2026-05-01','2026-05-04','[)'), 2, -500);

\echo 5.11 rating of 9 (booking 3 is checked out and has no review yet)
INSERT INTO reviews (booking_id, rating) VALUES (3, 9);

\echo 5.12 second review on the same booking (booking 1 already has one)
INSERT INTO reviews (booking_id, rating) VALUES (1, 4);

\echo 5.13 review on a booking that is not checked out (booking 2 is confirmed)
INSERT INTO reviews (booking_id, rating) VALUES (2, 4);

\echo 5.14 overlapping rate plan
INSERT INTO rate_plans (property_id, room_type_id, season_name, valid, nightly_rate)
VALUES (1, 1, 'Sneaky', daterange('2026-02-01','2026-03-01','[)'), 1000);

\echo
\echo ===== MUST SUCCEED (each block is rolled back afterwards) =====

\echo 5.15 checkout on the 5th, another check-in on the 5th
BEGIN;
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :r103, daterange('2026-06-01','2026-06-05','[)'), 2, 3800);
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (6, :r103, daterange('2026-06-05','2026-06-08','[)'), 2, 3800);
ROLLBACK;

\echo 5.16 cancelled booking 1-5 March, someone else books 2-6 March (booking 4 is the cancelled one)
BEGIN;
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate)
VALUES (5, :h301, daterange('2026-03-02','2026-03-06','[)'), 2, 7980);
ROLLBACK;

\echo 5.17 room 101 exists at all three properties (expect 3)
SELECT count(*) AS rooms_numbered_101 FROM rooms WHERE room_number = '101';

\echo 5.18 one booking receives three part-payments
BEGIN;
INSERT INTO payments (booking_id, amount, method) VALUES (2, 1000, 'cash');
INSERT INTO payments (booking_id, amount, method) VALUES (2, 1000, 'card');
INSERT INTO payments (booking_id, amount, method) VALUES (2, 1000, 'upi');
ROLLBACK;