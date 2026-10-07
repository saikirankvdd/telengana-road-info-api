import pytest
from backend.etl.normalizer import ETLNormalizer

def test_historical_csv_to_database_mapping():
    normalizer = ETLNormalizer()
    
    raw = {
        "internal_id": "INT_99",
        "tender_id": "TEND_1001",
        "ref_no": "REF/2024/TG/01",
        "title": "Road Widening from Uppal to Medchal",
        "org_name": "ROADS & BUILDINGS TELANGANA",
        "parsed_json": {
            "Name of the selected bidder(s)": "M/S KNR CONSTRUCTIONS PVT LTD",
            "Contract Value": "₹ 5,00,00,000",
            "Contract Date": "2024-03-15",
            "Location": "Medchal, Telangana"
        }
    }

    norm = normalizer.normalize_record(raw, "ROAD_WIDENING", "HIGH_RELEVANCE", "Matched road widening")
    
    # Mapping verification assertions
    assert norm["tender_id"] == "TEND_1001"
    assert norm["tender_reference_number"] == "REF/2024/TG/01"
    assert norm["project_name"] == "Road Widening from Uppal to Medchal"
    assert norm["normalized_contractor_name"] == "KNR"
    assert norm["selected_bidder"] == "M/S KNR CONSTRUCTIONS PVT LTD"
    assert norm["contract_value"] == 50000000.0
    assert norm["district"] == "MEDCHAL"
    assert norm["state"] == "Telangana"
