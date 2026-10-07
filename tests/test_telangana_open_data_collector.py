"""
Automated unit and integration tests for TelanganaOpenDataCollector.
Uses mocked API responses (httpx / pytest) to ensure zero dependency on live remote government APIs.
"""

import json
import pytest
import httpx
from unittest.mock import MagicMock, patch
from pathlib import Path
from scripts.collectors.telangana_open_data import TelanganaOpenDataCollector

@pytest.fixture
def sample_dkan_response():
    return [
        {
            "@type": "dcat:Dataset",
            "identifier": "e01b3d41-8a0c-415a-a9aa-888a0bba132c",
            "title": "Roads and Drainage Network in Urban Local Bodies",
            "description": "Geospatial and statistical data on roads and drainage infrastructure across ULBs in Telangana.",
            "keyword": ["road", "roads", "drainage", "infrastructure", "ulb"],
            "publisher": {"data": {"name": "Commissioner and Director of Municipal Administration"}},
            "modified": "2024-05-15T10:00:00Z",
            "distribution": [
                {
                    "identifier": "dist-1",
                    "data": {
                        "title": "Roads CSV Data",
                        "format": "csv",
                        "downloadURL": "https://data.telangana.gov.in/sites/default/files/roads.csv"
                    }
                }
            ]
        },
        {
            "@type": "dcat:Dataset",
            "identifier": "f1a3b556-05f9-4bfe-85d4-b19e77ac0138",
            "title": "Mission Kakatiya Phase 4",
            "description": "Tender and execution details of tank restoration works under Mission Kakatiya Phase 4.",
            "keyword": ["works", "tender", "irrigation"],
            "publisher": {"data": {"name": "Irrigation & CAD Department"}},
            "modified": "2023-11-20T14:30:00Z",
            "distribution": [
                {
                    "identifier": "dist-2",
                    "data": {
                        "title": "Phase 4 Works XLSX",
                        "format": "xlsx",
                        "downloadURL": "https://data.telangana.gov.in/sites/default/files/mk_phase4.xlsx"
                    }
                }
            ]
        },
        {
            "@type": "dcat:Dataset",
            "identifier": "irrelevant-101",
            "title": "Telangana Drugs Control Administration Data",
            "description": "Licenses issued for drug retail stores.",
            "keyword": ["pharmacy", "medicine"],
            "publisher": {"data": {"name": "Drugs Control Administration"}},
            "distribution": []
        }
    ]

def test_collector_initialization():
    collector = TelanganaOpenDataCollector(dry_run=True)
    assert collector.source_name == "Telangana Open Data Portal"
    assert collector.dry_run is True
    assert "https://data.telangana.gov.in" in collector.base_url

def test_checksum_generation(sample_dkan_response):
    collector = TelanganaOpenDataCollector()
    checksum1 = collector.compute_checksum(sample_dkan_response)
    checksum2 = collector.compute_checksum(sample_dkan_response)
    assert checksum1 == checksum2
    assert len(checksum1) == 64  # SHA-256 hex length

def test_successful_catalog_discovery(sample_dkan_response):
    collector = TelanganaOpenDataCollector(dry_run=True)

    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_dkan_response
        mock_get.return_value = mock_response

        catalog_res = collector.fetch_dataset_catalog()
        assert catalog_res["status"] == "SUCCESS"
        assert catalog_res["status_code"] == 200
        assert catalog_res["checksum"] is not None

        summary = collector.discover_and_classify(catalog_res)
        assert summary["api_reachable"] is True
        assert summary["total_datasets_discovered"] == 3
        assert summary["total_distributions_discovered"] == 2
        assert summary["relevant_datasets_count"] == 2
        assert summary["production_db_mutation_count"] == 0

def test_timeout_and_retry_handling():
    collector = TelanganaOpenDataCollector(max_retries=2, backoff_factor=0.01, timeout=0.1)

    with patch("httpx.Client.get", side_effect=httpx.TimeoutException("Connection timed out")):
        catalog_res = collector.fetch_dataset_catalog()
        assert catalog_res["status"] == "CONNECTION_FAILED"
        assert "timed out" in catalog_res["error"]

def test_malformed_json_handling():
    collector = TelanganaOpenDataCollector(max_retries=1, backoff_factor=0.01)

    with patch("httpx.Client.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_get.return_value = mock_response

        catalog_res = collector.fetch_dataset_catalog()
        assert catalog_res["status"] == "MALFORMED_RESPONSE"
        assert "JSONDecodeError" in catalog_res["error"]

def test_rate_limiting_429_handling(sample_dkan_response):
    collector = TelanganaOpenDataCollector(max_retries=2, backoff_factor=0.01)

    mock_resp_429 = MagicMock(status_code=429)
    mock_resp_200 = MagicMock(status_code=200)
    mock_resp_200.json.return_value = sample_dkan_response

    with patch("httpx.Client.get", side_effect=[mock_resp_429, mock_resp_200]):
        catalog_res = collector.fetch_dataset_catalog()
        assert catalog_res["status"] == "SUCCESS"
        assert catalog_res["status_code"] == 200

def test_safe_discovery_file_output(tmp_path, sample_dkan_response):
    test_out_file = tmp_path / "test_catalog.json"
    collector = TelanganaOpenDataCollector(dry_run=True)

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_dkan_response
        mock_get.return_value = mock_resp

        summary = collector.run_safe_discovery(output_path=str(test_out_file))
        assert test_out_file.exists()
        assert summary["safe_discovery_mode"] is True
        assert summary["production_db_mutation_count"] == 0

        with open(test_out_file, "r") as f:
            data = json.load(f)
            assert data["total_datasets_discovered"] == 3
            assert data["relevant_datasets_count"] == 2
