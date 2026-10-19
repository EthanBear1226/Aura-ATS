import os
from datetime import datetime
from unittest.mock import patch

import calendar_service as calendar
import models


def seed(db):
    person = models.Interviewer(name="Calendar Interviewer", role_type="Interviewer")
    candidate = models.Candidate(name="Calendar Candidate", job="Engineer", stage="初筛", skills=[])
    db.add_all([person, candidate])
    db.commit()
    return person, candidate


def payload(person, candidate, start="2026-11-02T09:00:00", end="2026-11-02T10:00:00"):
    return {"candidate_id": candidate.id, "interviewer_id": person.id,
            "interviewer_name": "ignored spoofed name", "job_title": "Engineer",
            "start_time": start, "end_time": end, "location": "Online"}


def availability(client, headers, person, day="2026-11-02"):
    return client.get(f"/api/calendar/freebusy?interviewer_id={person.id}&date={day}", headers=headers)


def test_calendar_local_overlap_cross_day_and_cancelled(client, db_session, admin_headers):
    person, candidate = seed(db_session)
    for start, end, status in [
        ("2026-11-02T09:30", "2026-11-02T10:30", "已安排"),
        ("2026-11-01T23:30", "2026-11-02T09:15", "已安排"),
        ("2026-11-02T11:00", "2026-11-02T12:00", "已取消"),
    ]:
        db_session.add(models.Interview(candidate_id=candidate.id, interviewer_name=person.name,
            start_time=datetime.fromisoformat(start), end_time=datetime.fromisoformat(end), status=status))
    db_session.commit()
    with patch.dict(os.environ, {"FEISHU_CALENDAR_ENABLED": "false"}):
        response = availability(client, admin_headers, person)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["external_status"] == "not_connected"
    slots = {slot["time"]: slot for slot in data["slots"]}
    assert not slots["09:00"]["isFree"] and not slots["10:00"]["isFree"]
    assert slots["11:00"]["isFree"] and slots["11:00"]["external_busy"] is None
    assert "飞书未检查" in slots["11:00"]["label"]


def test_calendar_rejects_invalid_date_missing_and_ambiguous_people(client, db_session, admin_headers):
    person, _ = seed(db_session)
    assert availability(client, admin_headers, person, "bad-date").status_code == 422
    assert client.get("/api/calendar/freebusy?date=2026-11-02&interviewer_id=999999", headers=admin_headers).status_code == 404
    db_session.add(models.Interviewer(name=person.name, role_type="Interviewer"))
    db_session.commit()
    assert availability(client, admin_headers, person).status_code == 409


def test_calendar_identity_admin_only_unique_and_cleanup(client, db_session, admin_headers, make_auth_headers):
    person, _ = seed(db_session)
    other = models.Interviewer(name="Other Person", role_type="Interviewer")
    db_session.add(other)
    db_session.commit()
    url = f"/api/settings/interviewers/{person.id}/calendar-identity"
    recruiter = make_auth_headers("calendar-hr@test.local", "Recruiter", "HR")
    assert client.get(url, headers=recruiter).status_code == 403
    assert client.patch(url, json={"feishu_open_id": "ou_testing"}, headers=recruiter).status_code == 403
    assert client.delete(url, headers=recruiter).status_code == 403
    assert client.patch(url, json={"feishu_open_id": "bad"}, headers=admin_headers).status_code == 422
    assert client.patch(url, json={"feishu_open_id": "ou_testing"}, headers=admin_headers).status_code == 200
    assert client.get(url, headers=admin_headers).json()["feishu_open_id"] == "ou_testing"
    assert client.patch(f"/api/settings/interviewers/{other.id}/calendar-identity",
                        json={"feishu_open_id": "ou_testing"}, headers=admin_headers).status_code == 409
    assert client.delete(url, headers=admin_headers).status_code == 200
    assert client.get(url, headers=admin_headers).json()["feishu_open_id"] is None
    client.patch(url, json={"feishu_open_id": "ou_testing"}, headers=admin_headers)
    assert client.delete(f"/api/settings/interviewers/{person.id}", headers=admin_headers).status_code == 200
    db_session.expire_all()
    assert db_session.query(models.CalendarIdentity).count() == 0


def test_calendar_enabled_without_real_connection_blocks_booking(client, db_session, admin_headers):
    person, candidate = seed(db_session)
    with patch.dict(os.environ, {"FEISHU_CALENDAR_ENABLED": "true"}):
        assert availability(client, admin_headers, person).json()["external_status"] == "unbound"
        db_session.add(models.CalendarIdentity(interviewer_id=person.id, feishu_open_id="ou_pending"))
        db_session.commit()
        data = availability(client, admin_headers, person).json()
        assert data["external_status"] == "unavailable"
        assert all(not slot["isFree"] and slot["external_busy"] is None for slot in data["slots"])
        response = client.post("/api/interviews", json=payload(person, candidate), headers=admin_headers)
        assert response.status_code == 503, response.text
    assert db_session.query(models.Interview).count() == 0
    db_session.refresh(candidate)
    assert candidate.stage == "初筛"


def test_calendar_provider_busy_free_and_failure_contract(client, db_session, admin_headers):
    person, candidate = seed(db_session)
    db_session.add(models.CalendarIdentity(interviewer_id=person.id, feishu_open_id="ou_mock_test"))
    db_session.commit()
    class TestProvider:
        def busy_intervals(self, identity, start, end):
            assert start.utcoffset().total_seconds() == 8 * 3600
            return [calendar.BusyInterval(datetime.fromisoformat("2026-11-02T01:30:00+00:00"),
                                          datetime.fromisoformat("2026-11-02T02:30:00+00:00"))]
    with patch.dict(os.environ, {"FEISHU_CALENDAR_ENABLED": "true"}), patch.object(calendar, "build_provider", return_value=TestProvider()):
        data = availability(client, admin_headers, person).json()
        assert data["external_status"] == "connected"
        slots = {slot["time"]: slot for slot in data["slots"]}
        assert slots["09:00"]["external_busy"] and not slots["10:00"]["isFree"]
        assert slots["11:00"]["isFree"] and slots["11:00"]["external_busy"] is False
        assert client.post("/api/interviews", json=payload(person, candidate), headers=admin_headers).status_code == 409
        with patch.object(TestProvider, "busy_intervals", side_effect=TimeoutError("secret transport detail")):
            data = availability(client, admin_headers, person).json()
            assert data["external_status"] == "unavailable"
            assert "secret" not in str(data)
        with patch.object(TestProvider, "busy_intervals", return_value=[calendar.BusyInterval(datetime(2026, 11, 2, 9), datetime(2026, 11, 2, 10))]):
            assert availability(client, admin_headers, person).json()["external_status"] == "unavailable"


def test_booking_rechecks_overlap_and_normalizes_timezone(client, db_session, admin_headers):
    person, candidate = seed(db_session)
    with patch.dict(os.environ, {"FEISHU_CALENDAR_ENABLED": "false"}):
        body = payload(person, candidate, "2026-11-02T01:00:00Z", "2026-11-02T02:00:00Z")
        response = client.post("/api/interviews", json=body, headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["interviewer_name"] == person.name
        assert response.json()["start_time"].startswith("2026-11-02T09:00")
        assert client.post("/api/interviews", json=payload(person, candidate), headers=admin_headers).status_code == 409
        assert client.post("/api/interviews", json=payload(person, candidate, "2026-11-02T10:00", "2026-11-02T11:00"), headers=admin_headers).status_code == 200
        for start, end in [("2026-11-03T09:00", "2026-11-03T09:00"), ("2026-11-03T10:00", "2026-11-03T09:00"), ("2026-11-03T09:00", "2026-11-03T18:00")]:
            assert client.post("/api/interviews", json=payload(person, candidate, start, end), headers=admin_headers).status_code == 422
    assert db_session.query(models.Interview).count() == 2


def test_calendar_and_booking_authorization(client, db_session, make_auth_headers):
    person, candidate = seed(db_session)
    interviewer = make_auth_headers("calendar-viewer@test.local", "Interviewer", person.name)
    other = make_auth_headers("calendar-other@test.local", "Interviewer", "Other")
    assert availability(client, {}, person).status_code == 401
    assert availability(client, other, person).status_code == 403
    with patch.dict(os.environ, {"FEISHU_CALENDAR_ENABLED": "false"}):
        assert availability(client, interviewer, person).status_code == 200
    assert client.post("/api/interviews", json=payload(person, candidate), headers=interviewer).status_code == 403
