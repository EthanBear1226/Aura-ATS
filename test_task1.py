import unittest
from datetime import datetime
from pydantic import ValidationError

# We will import models and schemas
# Since they are not updated yet, these imports or instantiations will fail
import models
import schemas
from database import SessionLocal, engine

class TestTask1ModelsAndSchemas(unittest.TestCase):
    def setUp(self):
        models.Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        # Optionally, drop tables or rollback, but let's keep it simple

    def test_email_template_model(self):
        # This will fail if EmailTemplate is not in models
        template = models.EmailTemplate(name="Test", subject="Sub", content="Content")
        self.assertEqual(template.name, "Test")

    def test_feedback_template_model(self):
        # This will fail if FeedbackTemplate is not in models
        template = models.FeedbackTemplate(name="TestFB", content="ContentFB")
        self.assertEqual(template.name, "TestFB")

    def test_interview_model(self):
        # This will fail if Interview is not in models
        now = datetime.utcnow()
        interview = models.Interview(
            candidate_id=1,
            interviewer_name="Alice",
            job_title="Engineer",
            start_time=now,
            end_time=now,
            location="Room 1"
        )
        self.db.add(interview)
        self.db.commit()
        self.db.refresh(interview)
        self.assertEqual(interview.status, "已安排") # checking default

    def test_schemas(self):
        # This will fail if schemas are not present
        email_schema = schemas.EmailTemplateCreate(name="Test", subject="Sub", content="Content")
        self.assertEqual(email_schema.name, "Test")
        
        fb_schema = schemas.FeedbackTemplateCreate(name="TestFB", content="ContentFB")
        self.assertEqual(fb_schema.name, "TestFB")
        
        now = datetime.utcnow()
        interview_create = schemas.InterviewCreate(
            candidate_id=1,
            interviewer_name="Alice",
            job_title="Engineer",
            start_time=now,
            end_time=now,
            location="Room 1"
        )
        self.assertEqual(interview_create.job_title, "Engineer")
        
        interview_update = schemas.InterviewUpdateFeedback(
            feedback_result="满意",
            feedback_text="Good"
        )
        self.assertEqual(interview_update.feedback_result, "满意")

if __name__ == '__main__':
    unittest.main()
