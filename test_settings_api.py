def test_settings_departments(client, admin_headers):
    # Delete all existing to start fresh or just append and delete
    # GET
    response = client.get("/api/settings/departments", headers=admin_headers)
    assert response.status_code == 200
    initial_count = len(response.json())
    
    # POST
    payload = {"name": "Test Department"}
    response = client.post("/api/settings/departments", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Department"
    assert "id" in data
    item_id = data["id"]
    
    # DELETE
    response = client.delete(f"/api/settings/departments/{item_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_settings_interviewers(client, admin_headers):
    response = client.get("/api/settings/interviewers", headers=admin_headers)
    assert response.status_code == 200, response.text
    
    payload = {"name": "Test Interviewer", "role_type": "Manager"}
    response = client.post("/api/settings/interviewers", json=payload, headers=admin_headers)
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/interviewers/{item_id}", headers=admin_headers)
    assert response.status_code == 200, response.text

def test_settings_locations(client, admin_headers):
    response = client.get("/api/settings/locations", headers=admin_headers)
    assert response.status_code == 200
    
    payload = {"name": "Test Location", "type": "线上"}
    response = client.post("/api/settings/locations", json=payload, headers=admin_headers)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/locations/{item_id}", headers=admin_headers)
    assert response.status_code == 200

def test_settings_interview_processes(client, admin_headers):
    response = client.get("/api/settings/interview-processes", headers=admin_headers)
    assert response.status_code == 200
    
    payload = {"name": "Test Process", "stages": "测试"}
    response = client.post("/api/settings/interview-processes", json=payload, headers=admin_headers)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/interview-processes/{item_id}", headers=admin_headers)
    assert response.status_code == 200

def test_settings_categories(client, admin_headers):
    response = client.get("/api/settings/categories", headers=admin_headers)
    assert response.status_code == 200
    
    payload = {"name": "Test Category"}
    response = client.post("/api/settings/categories", json=payload, headers=admin_headers)
    assert response.status_code == 200
    item_id = response.json()["id"]
    
    response = client.delete(f"/api/settings/categories/{item_id}", headers=admin_headers)
    assert response.status_code == 200

