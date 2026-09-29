def bookings_gen():
    rows = [(1, "Asha"), (2, "Ravi"), (3, "Meena")]

    for row in rows:
        print("  before yield")
        yield row

    print("  after loop (cleanup happens here)")


for row in bookings_gen():
    print("got", row)