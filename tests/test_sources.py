def test_list_sources(client):
    response = client.get("/api/v1/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_source_by_id(client):
    response = client.get("/api/v1/sources/1")
    assert response.status_code == 200
    data = response.json()
    assert "source_name" in data
    assert "source_type" in data
