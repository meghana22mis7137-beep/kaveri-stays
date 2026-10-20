import threading
import httpx

def call(name):
    r = httpx.get("http://127.0.0.1:8000/slow", timeout=10)
    print(name, r.json())

t1 = threading.Thread(target=call, args=("A",))
t2 = threading.Thread(target=call, args=("B",))
t1.start(); t2.start()
t1.join(); t2.join()