"""Stable assignment and conservative compatibility for historical records."""

from sqlalchemy import inspect, text
import models


def upgrade_interview_identity(engine):
    # Introspection works for SQLite and the production SQLAlchemy dialect.
    columns = {column["name"] for column in inspect(engine).get_columns("interviews")}
    with engine.begin() as conn:
        if "interviewer_id" not in columns:
            conn.execute(text("ALTER TABLE interviews ADD COLUMN interviewer_id INTEGER"))
        conn.execute(text(
            "UPDATE interviews SET interviewer_id = "
            "(SELECT MIN(id) FROM interviewers WHERE interviewers.name = interviews.interviewer_name) "
            "WHERE interviewer_id IS NULL AND "
            "(SELECT COUNT(*) FROM interviewers WHERE interviewers.name = interviews.interviewer_name) = 1"
        ))


def account_person(db, user):
    binding = db.query(models.InterviewerAccount).filter_by(user_id=user.id).first()
    if binding:
        return db.query(models.Interviewer).filter_by(id=binding.interviewer_id).first()
    # Lazily persist only unambiguous historical account mappings.
    if db.query(models.User).filter_by(name=user.name, role="Interviewer").count() != 1:
        return None
    people = db.query(models.Interviewer).filter_by(name=user.name).all()
    if len(people) != 1:
        return None
    person = people[0]
    if db.query(models.InterviewerAccount).filter_by(interviewer_id=person.id).first():
        return None
    from sqlalchemy.exc import IntegrityError
    try:
        with db.begin_nested():
            db.add(models.InterviewerAccount(interviewer_id=person.id, user_id=user.id))
            db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        binding = db.query(models.InterviewerAccount).filter_by(user_id=user.id).first()
        return db.query(models.Interviewer).filter_by(id=binding.interviewer_id).first() if binding else None
    return person


def legacy_name_allowed(db, user):
    if not user.name or db.query(models.User).filter_by(name=user.name, role="Interviewer").count() != 1:
        return False
    people = db.query(models.Interviewer).filter_by(name=user.name).all()
    if len(people) > 1:
        return False
    binding = db.query(models.InterviewerAccount).filter_by(user_id=user.id).first()
    if binding and (not people or binding.interviewer_id != people[0].id):
        return False
    if people:
        owner = db.query(models.InterviewerAccount).filter_by(interviewer_id=people[0].id).first()
        if owner and owner.user_id != user.id:
            return False
    return True


def freeze_legacy_assignments(db, person):
    """Capture unambiguous old names before rename or explicit account binding."""
    if db.query(models.Interviewer).filter_by(name=person.name).count() != 1:
        return
    db.query(models.Interview).filter(
        models.Interview.interviewer_id.is_(None), models.Interview.interviewer_name == person.name
    ).update({models.Interview.interviewer_id: person.id}, synchronize_session=False)
    users = db.query(models.User).filter_by(name=person.name, role="Interviewer").all()
    if len(users) == 1 and not db.query(models.InterviewerAccount).filter_by(interviewer_id=person.id).first():
        if not db.query(models.InterviewerAccount).filter_by(user_id=users[0].id).first():
            db.add(models.InterviewerAccount(interviewer_id=person.id, user_id=users[0].id))
