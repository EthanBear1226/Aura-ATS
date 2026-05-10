import os
from fastapi.testclient import TestClient

# Set up test database or use the existing one for simplicity
# In a real scenario we'd mock or override the DB dependency
from main import app, get_db
from database import SessionLocal, Base, engine

# Create tables for testing if they don't exist
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_settings_departments():
    # Delete all existing to start fresh or just append and delete
    # GET
    response = client.get("/api/settings/departments")
    assert response.status_code == 200
    initial_count = len(response.json())
    
    # POST
    payload = {"name": "Test Department"}
    response = client.post("/api/settings/departments", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Department"
    assert "id" in data
    item_id = data["id"]
    
    # DELETE
    response = client.delete(f"/api/settings/departments/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_settings_interviewers():
    response = client.get("/api/settings/interviewers")
    assert response.status_code == 200, response.text
    
    payload = {"name": "Test Interviewer", "role_type": "Manager"}
    response = client.post("/api/settings/interviewers", json=payload)
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/interviewers/{item_id}")
    assert response.status_code == 200, response.text

def test_settings_locations():
    response = client.get("/api/settings/locations")
    assert response.status_code == 200
    
    payload = {"name": "Test Location", "type": "线上"}
    response = client.post("/api/settings/locations", json=payload)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/locations/{item_id}")
    assert response.status_code == 200

def test_settings_interview_processes():
    response = client.get("/api/settings/interview-processes")
    assert response.status_code == 200
    
    payload = {"name": "Test Process", "stages": "测试"}
    response = client.post("/api/settings/interview-processes", json=payload)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/interview-processes/{item_id}")
    assert response.status_code == 200

def test_settings_categories():
    response = client.get("/api/settings/categories")
    assert response.status_code == 200
    
    payload = {"name": "Test Category"}
    response = client.post("/api/settings/categories", json=payload)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/categories/{item_id}")
    assert response.status_code == 200

if __name__ == "__main__":
    test_settings_departments()
    test_settings_interviewers()
    test_settings_locations()
    test_settings_interview_processes()
    test_settings_categories()
    print("All tests passed!")
