import pytest
from datetime import date
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nights import nights

def test_one_night():
    assert nights(date(2026, 3, 1), date(2026, 3, 2)) == 1

def test_five_nights():
    assert nights(date(2026, 3, 1), date(2026, 3, 6)) == 5

def test_zero_nights():
    with pytest.raises(ValueError):
        nights(date(2026, 3, 1), date(2026, 3, 1))

def test_checkout_before_checkin():
    with pytest.raises(ValueError):
        nights(date(2026, 3, 5), date(2026, 3, 1))

@pytest.mark.parametrize("a,b,expected", [
    (date(2026, 3, 1), date(2026, 3, 2), 1),
    (date(2026, 12, 24), date(2026, 12, 27), 3),
])
def test_parametrised(a, b, expected):
    assert nights(a, b) == expected

app = FastAPI()

@app.get("/hello")
def hello():
    return {"msg": "hi"}

client = TestClient(app)

def test_hello():
    r = client.get("/hello")
    assert r.status_code == 200
    assert r.json() == {"msg": "hi"}