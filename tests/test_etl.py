import pytest
from backend.etl.telangana_filter import TelanganaFilter
from backend.etl.project_classifier import ProjectClassifier
from backend.etl.normalizer import ETLNormalizer
from backend.etl.deduplicator import ETLDeduplicator
from backend.etl.validator import ETLValidator

def test_telangana_filter():
    tg_filter = TelanganaFilter()
    
    tg_record = {"org_name": "GREATER HYDERABAD MUNICIPAL CORPORATION", "title": "Construction of Flyover at Uppal"}
    non_tg_record = {"org_name": "DELHI DEVELOPMENT AUTHORITY", "title": "Park Beautification"}

    assert tg_filter.is_telangana_record(tg_record) is True
    assert tg_filter.is_telangana_record(non_tg_record) is False

def test_project_classifier():
    classifier = ProjectClassifier()

    flyover_record = {"title": "Construction of Flyover at Uppal Junction"}
    road_record = {"title": "Road Widening and Resurfacing Work"}
    infra_record = {"title": "Junction Improvement and SRDP Corridor Work"}

    cat1, rel1, _ = classifier.classify(flyover_record)
    assert cat1 == "FLYOVER"
    assert rel1 == "HIGH_RELEVANCE"

    cat2, rel2, _ = classifier.classify(road_record)
    assert cat2 in ["ROAD", "ROAD_WIDENING"]
    assert rel2 == "HIGH_RELEVANCE"

    cat3, rel3, _ = classifier.classify(infra_record)
    assert cat3 in ["ROAD_DEVELOPMENT", "CORRIDOR", "OTHER_INFRASTRUCTURE"]
    assert rel3 in ["HIGH_RELEVANCE", "POSSIBLE_RELEVANCE"]

def test_normalizer():
    normalizer = ETLNormalizer()
    
    raw = {
        "tender_id": "12345",
        "ref_no": "NIT/2023/001",
        "title": "Construction of Elevated Corridor",
        "org_name": "RO HYDERABAD",
        "parsed_json": {
            "Name of the selected bidder(s)": "M/S KNR CONSTRUCTIONS LTD",
            "Contract Value": "₹ 1,50,00,000",
            "Contract Date": "2023-05-15"
        }
    }

    norm = normalizer.normalize_record(raw, "FLYOVER / GRADE SEPARATOR", "HIGH_RELEVANCE", "Matched flyover")
    assert norm["tender_id"] == "12345"
    assert norm["original_contractor_name"] == "M/S KNR CONSTRUCTIONS LTD"
    assert norm["normalized_contractor_name"] == "KNR"
    assert norm["awarded_value"] == 15000000.0

def test_deduplicator():
    dedup = ETLDeduplicator()

    record1 = {"tender_id": "T1001", "tender_reference_number": "REF01", "title": "Flyover Construction", "organisation": "GHMC", "aoc_date": "2022-01-01"}
    record2 = {"tender_id": "T1001", "tender_reference_number": "REF01", "title": "Flyover Construction", "organisation": "GHMC", "aoc_date": "2022-01-01"}

    is_dup1, key1 = dedup.process(record1)
    is_dup2, key2 = dedup.process(record2)

    assert is_dup1 is False
    assert is_dup2 is True
    assert "EXACT_TENDER_ID_T1001" in key2

def test_validator():
    validator = ETLValidator()

    valid_record = {
        "tender_id": "T1",
        "title": "Road Development",
        "organisation": "GHMC",
        "relevance_rating": "HIGH_RELEVANCE",
        "original_contractor_name": "L&T Construction",
        "awarded_value": 50000000.0
    }

    status = validator.validate_record(valid_record, is_duplicate=False)
    assert status == "VALID"
