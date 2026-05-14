import unittest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, engine
import models

client = TestClient(app)

class TestTask2API(unittest.TestCase):
    def setUp(self):
        models.Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
        # Insert a candidate to use for interview creation
        self.candidate = models.Candidate(
            name="Test Candidate",
            job="Test Job",
            stage="初筛",
            exp="本科",
            phone="12345678901",
            email="test@candidate.com"
        )
        self.db.add(self.candidate)
        self.db.commit()
        self.db.refresh(self.candidate)

        # Insert email template
        self.email_template = models.EmailTemplate(
            name="Default",
            subject="Interview for {job_title}",
            content="Hello {candidate_name}, you have an interview for {job_title} at {interview_time} in {location}."
        )
        self.db.add(self.email_template)
        self.db.commit()

    def tearDown(self):
        self.db.query(models.Interview).delete()
        self.db.query(models.EmailTemplate).delete()
        self.db.query(models.Candidate).filter(models.Candidate.id == self.candidate.id).delete()
        self.db.commit()
        self.db.close()

    def test_get_email_templates(self):
        response = client.get("/api/settings/email-templates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_feedback_templates(self):
        response = client.get("/api/settings/feedback-templates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_freebusy(self):
        response = client.get("/api/calendar/freebusy?interviewer=test@interviewer.com&date=2026-05-13")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertIn("time", data[0])
        self.assertIn("isFree", data[0])

    def test_create_interview(self):
        payload = {
            "candidate_id": self.candidate.id,
            "interviewer_name": "test@interviewer.com",
            "job_title": "Test Job",
            "start_time": "2026-05-13T10:00:00",
            "end_time": "2026-05-13T11:00:00",
            "location": "Zoom"
        }
        response = client.post("/api/interviews", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["job_title"], "Test Job")
        self.assertEqual(data["status"], "已安排")
        self.assertIsNotNone(data["id"])

    def test_get_interviews(self):
        response = client.get("/api/interviews")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_submit_feedback(self):
        # Create an interview first
        payload = {
            "candidate_id": self.candidate.id,
            "interviewer_name": "test@interviewer.com",
            "job_title": "Test Job",
            "start_time": "2026-05-13T10:00:00",
            "end_time": "2026-05-13T11:00:00",
            "location": "Zoom"
        }
        create_res = client.post("/api/interviews", json=payload)
        interview_id = create_res.json()["id"]

        feedback_payload = {
            "feedback_result": "通过",
            "feedback_text": "Good performance"
        }
        response = client.patch(f"/api/interviews/{interview_id}/feedback", json=feedback_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["feedback_result"], "通过")
        self.assertEqual(data["feedback_text"], "Good performance")
        self.assertEqual(data["status"], "已完成")

if __name__ == '__main__':
    unittest.main()
