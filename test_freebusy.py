from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

res = client.get("/api/calendar/freebusy?interviewer=test@interviewer.com&date=2026-05-13")
print("Free/Busy:", res.json())
