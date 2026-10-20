import time
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

@app.get("/slow")
def slow():
    start = datetime.now().strftime("%H:%M:%S.%f")
    time.sleep(3)
    end = datetime.now().strftime("%H:%M:%S.%f")
    return {"start": start, "end": end}