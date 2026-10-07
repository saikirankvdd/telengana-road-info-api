def test_list_projects(client):
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_nonexistent_project(client):
    response = client.get("/api/v1/projects/999999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
