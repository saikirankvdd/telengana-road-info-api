def test_list_roads(client):
    response = client.get("/api/v1/roads")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_nonexistent_road(client):
    response = client.get("/api/v1/roads/999999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
