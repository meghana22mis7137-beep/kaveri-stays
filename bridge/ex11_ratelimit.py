import time

hits: dict[str, list[float]] = {}
LIMIT = 5
WINDOW = 60

def allowed(key: str) -> bool:
    now = time.time()
    recent = [t for t in hits.get(key, []) if now - t < WINDOW]
    if len(recent) >= LIMIT:
        hits[key] = recent
        return False
    recent.append(now)
    hits[key] = recent
    return True

for i in range(8):
    print(i + 1, allowed("1.2.3.4"))