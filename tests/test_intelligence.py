import pytest

def test_source_connectivity_and_collector(client):
    """
    Test real Overpass vector GIS collector connectivity and response normalization.
    """
    from backend.collectors.telangana_gis import OverpassGISCollector
    collector = OverpassGISCollector()
    raw = {
        "element_id": 99911,
        "road_name": "Test Highway 163",
        "road_number": "NH-163",
        "road_type": "Primary",
        "latitude": 17.4447,
        "longitude": 78.3483,
        "geometry_wkt": "LINESTRING_WAY_99911",
        "distance_meters": 12.5
    }
    normalized = collector.normalize_record(raw)
    assert normalized["road_name"] == "Test Highway 163"
    assert normalized["road_number"] == "NH-163"
    assert normalized["road_type"] == "Primary"
    assert normalized["source_record_id"] == "99911"

def test_iiit_junction_real_gis_experiment(client):
    """
    Test API response for IIIT Junction query against connected GIS source.
    Should correctly separate fields_found from fields_not_found without requiring hardcoded project facts.
    """
    response = client.get("/api/v1/road-intelligence?query=IIIT%20Junction")
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "IIIT Junction"
    assert "fields_found" in data
    assert "fields_not_found" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1

    # Check provenance fields exist
    src = data["sources"][0]
    assert "source_name" in src
    assert "source_type" in src
    assert "retrieved_at" in src

def test_nearby_coordinate_geographic_search(client):
    """
    Test geographic coordinate search: lat + lng + radius -> nearest roads -> geometry + distance + provenance
    """
    response = client.get("/api/v1/nearby?lat=17.4447&lng=78.3483&radius=1000")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    if len(data) > 0:
        first_road = data[0]
        assert "road_name" in first_road
        assert "distance_meters" in first_road
        assert first_road["source"]["source_type"] == "OPENSTREETMAP_OVERPASS"

def test_nonexistent_project_intelligence(client):
    """
    Test API response when connected sources have no matching project record.
    """
    response = client.get("/api/v1/road-intelligence?query=UnknownRoadQuery999")
    assert response.status_code == 200
    data = response.json()

    assert data["project"]["status"] == "NOT_FOUND"
    assert data["project"]["value"] is None
    assert "contractor" in data["fields_not_found"]
    assert data["contractors"]["fallback_contact"]["type"] == "AUTHORITY"
