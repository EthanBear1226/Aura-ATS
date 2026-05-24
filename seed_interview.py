from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
if db.query(models.Interview).count() == 0:
    interview = models.Interview(
        candidate_id=1,
        interviewer_name="Test Interviewer",
        job_title="Test Job",
        start_time=datetime.now(),
        end_time=datetime.now(),
        location="Online",
        status="已安排"
    )
    db.add(interview)
    db.commit()
    print("Seeded interview.")
db.close()
