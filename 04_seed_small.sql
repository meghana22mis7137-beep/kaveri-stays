-- Small starter data. Safe to rerun: it wipes the tables first.
TRUNCATE reviews, payments, bookings, rate_plans, guests, rooms, room_types, properties
    RESTART IDENTITY CASCADE;

INSERT INTO properties (name, city, star_rating) VALUES
    ('Kaveri Riverside', 'Coorg', 4),
    ('Kaveri Hilltop', 'Ooty', 5),
    ('Kaveri Backwater', 'Alleppey', 4);

INSERT INTO room_types (name, max_occupancy) VALUES
    ('Standard', 2),
    ('Deluxe', 3),
    ('Suite', 4);

-- 12 rooms per property: 101-104 Standard, 201-204 Deluxe, 301-304 Suite
INSERT INTO rooms (property_id, room_number, room_type_id)
SELECT p.property_id, v.room_number, rt.room_type_id
FROM properties p
CROSS JOIN (VALUES
    ('101','Standard'),('102','Standard'),('103','Standard'),('104','Standard'),
    ('201','Deluxe'),  ('202','Deluxe'),  ('203','Deluxe'),  ('204','Deluxe'),
    ('301','Suite'),   ('302','Suite'),   ('303','Suite'),   ('304','Suite')
) AS v(room_number, type_name)
JOIN room_types rt ON rt.name = v.type_name;

-- 4 seasons per property per room type. Periods touch but never overlap.
INSERT INTO rate_plans (property_id, room_type_id, season_name, valid, nightly_rate)
SELECT p.property_id, rt.room_type_id, s.season_name, s.valid, ROUND(s.base * m.mult, 2)
FROM properties p
CROSS JOIN room_types rt
JOIN (VALUES ('Standard', 1.0), ('Deluxe', 1.4), ('Suite', 2.1)) AS m(type_name, mult)
    ON m.type_name = rt.name
CROSS JOIN (VALUES
    ('Regular 2025',   daterange('2025-01-01','2025-10-01','[)'), 3500.00),
    ('Monsoon 2025',   daterange('2025-10-01','2025-12-20','[)'), 2800.00),
    ('Christmas 2025', daterange('2025-12-20','2026-01-05','[)'), 7000.00),
    ('Regular 2026',   daterange('2026-01-05','2027-01-01','[)'), 3800.00)
) AS s(season_name, valid, base);

INSERT INTO guests (full_name, email, phone, city) VALUES
    ('Aarav Sharma', 'aarav.sharma@example.com', '+919876543210', 'Bengaluru'),
    ('Anita Desai',  'anita.desai@example.com',  '+919123456789', 'Mumbai'),
    ('Ben Carter',   'ben.carter@example.org',   '+447700900123', 'Bristol'),
    ('Chloe Dubois', 'chloe.dubois@example.com', '+33612345678',  'Lyon'),
    ('Elena Rossi',  'elena.rossi@example.com',  '+393201234567', 'Milan'),
    ('Kavya Nair',   'kavya.nair@example.com',   '+919456789012', 'Kochi');

-- Booking 1: checked out. Booking 3 starts the day booking 1 ends (rule 5).
INSERT INTO bookings (guest_id, room_id, stay, guests_count, nightly_rate, status) VALUES
    (1, (SELECT r.room_id FROM rooms r JOIN properties p USING (property_id)
         WHERE p.name = 'Kaveri Riverside' AND r.room_number = '101'),
     daterange('2026-01-10','2026-01-14','[)'), 2, 3800.00, 'checked_out'),
    (2, (SELECT r.room_id FROM rooms r JOIN properties p USING (property_id)
         WHERE p.name = 'Kaveri Riverside' AND r.room_number = '201'),
     daterange('2026-12-10','2026-12-13','[)'), 2, 5320.00, 'confirmed'),
    (3, (SELECT r.room_id FROM rooms r JOIN properties p USING (property_id)
         WHERE p.name = 'Kaveri Riverside' AND r.room_number = '101'),
     daterange('2026-01-14','2026-01-16','[)'), 1, 3800.00, 'checked_out'),
    (4, (SELECT r.room_id FROM rooms r JOIN properties p USING (property_id)
         WHERE p.name = 'Kaveri Hilltop' AND r.room_number = '301'),
     daterange('2026-03-01','2026-03-05','[)'), 3, 7980.00, 'cancelled');

INSERT INTO payments (booking_id, amount, method) VALUES
    (1, 15200.00, 'card'),
    (2, 5000.00,  'upi');

INSERT INTO reviews (booking_id, rating, comments) VALUES
    (1, 5, 'Peaceful stay by the river.');
    