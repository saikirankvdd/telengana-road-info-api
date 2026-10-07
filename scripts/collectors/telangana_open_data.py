"""
Telangana Open Data Portal Live API Collector (DKAN Metastore API)
Phase 4C Step 1 — Safe Discovery Collector

Target Source: Telangana Open Data Portal (https://data.telangana.gov.in/)
API Endpoint: https://data.telangana.gov.in/api/1/metastore/schemas/dataset/items

SAFETY CONSTRAINTS:
- Operating in SAFE DISCOVERY MODE (dry_run=True).
- ZERO insertion or mutation into production database tables (projects, tenders, contracts, contractors, authorities).
- Output stored strictly in data/live_discovery/telangana_open_data_catalog.json.
"""

import json
import logging
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TelanganaOpenDataCollector")

class TelanganaOpenDataCollector:
    """
    Collector for official Telangana Open Data Portal using DKAN 2.0 metastore REST API.
    Designed for robust error handling, retries, rate limiting, and safe discovery.
    """
    DEFAULT_BASE_URL = "https://data.telangana.gov.in/api/1/metastore/schemas/dataset/items"
    DEFAULT_USER_AGENT = "TelanganaRoadIntelAPI/1.0 (Safe Discovery)"

    # Keywords for domain filtering relevant to road infrastructure
    RELEVANT_KEYWORDS = [
        "road", "roads", "infrastructure", "highway", "bridge", "flyover",
        "transport", "works", "project", "r&b", "panchayat raj", "ghmc",
        "hmda", "tender", "contract", "construction", "drainage"
    ]

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        requests_per_minute: int = 60,
        dry_run: bool = True
    ):
        self.source_name = "Telangana Open Data Portal"
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limit_delay = 60.0 / float(requests_per_minute)
        self.dry_run = dry_run
        self.last_request_time = 0.0

    def _apply_rate_limit(self) -> None:
        """Enforces request rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def compute_checksum(self, payload: bytes | str | Dict[str, Any] | List[Any]) -> str:
        """Computes deterministic SHA-256 checksum of payload."""
        if isinstance(payload, (dict, list)):
            encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        elif isinstance(payload, str):
            encoded = payload.encode("utf-8")
        else:
            encoded = payload
        return hashlib.sha256(encoded).hexdigest()

    def fetch_dataset_catalog(self, client: Optional[httpx.Client] = None) -> Dict[str, Any]:
        """
        Fetches full dataset metadata catalog from DKAN metastore endpoint with retry logic.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        }

        retries = 0
        current_delay = 1.0

        while retries <= self.max_retries:
            self._apply_rate_limit()
            try:
                logger.info(f"Connecting to Telangana Open Data API: {self.base_url} (Attempt {retries + 1})")
                
                # Support passing external client or creating one
                if client:
                    response = client.get(self.base_url, headers=headers, timeout=self.timeout)
                else:
                    with httpx.Client(timeout=self.timeout, follow_redirects=True) as http_client:
                        response = http_client.get(self.base_url, headers=headers)

                status_code = response.status_code
                if status_code == 200:
                    try:
                        raw_data = response.json()
                        checksum = self.compute_checksum(raw_data)
                        return {
                            "status": "SUCCESS",
                            "status_code": 200,
                            "raw_payload": raw_data,
                            "checksum": checksum,
                            "retrieved_at": datetime.now(timezone.utc).isoformat()
                        }
                    except json.JSONDecodeError as err:
                        logger.error(f"Malformed JSON response received from API: {err}")
                        return {
                            "status": "MALFORMED_RESPONSE",
                            "status_code": 200,
                            "error": f"JSONDecodeError: {err}",
                            "checksum": None,
                            "retrieved_at": datetime.now(timezone.utc).isoformat()
                        }
                elif status_code == 429:
                    logger.warning(f"Rate limited (429). Retrying after backoff {current_delay}s...")
                elif status_code >= 500:
                    logger.warning(f"Server error ({status_code}). Retrying after backoff {current_delay}s...")
                else:
                    logger.error(f"API request failed with status code {status_code}")
                    return {
                        "status": "API_ERROR",
                        "status_code": status_code,
                        "error": f"HTTP {status_code}",
                        "checksum": None,
                        "retrieved_at": datetime.now(timezone.utc).isoformat()
                    }

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                logger.warning(f"Network request exception: {exc}. Attempt {retries + 1}/{self.max_retries + 1}")
                if retries == self.max_retries:
                    return {
                        "status": "CONNECTION_FAILED",
                        "status_code": 0,
                        "error": str(exc),
                        "checksum": None,
                        "retrieved_at": datetime.now(timezone.utc).isoformat()
                    }

            retries += 1
            time.sleep(current_delay)
            current_delay *= self.backoff_factor

        return {
            "status": "MAX_RETRIES_EXCEEDED",
            "status_code": 0,
            "error": "Exceeded maximum retry attempts",
            "checksum": None,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }

    def discover_and_classify(self, catalog_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses raw DKAN metastore response, discovers datasets & distributions,
        and classifies datasets relevant to roads and government works.
        """
        if catalog_response.get("status") != "SUCCESS":
            return {
                "source_name": self.source_name,
                "base_url": self.base_url,
                "api_reachable": False,
                "api_status_code": catalog_response.get("status_code", 0),
                "error": catalog_response.get("error"),
                "retrieved_at": catalog_response.get("retrieved_at"),
                "total_datasets_discovered": 0,
                "total_distributions_discovered": 0,
                "relevant_datasets_count": 0,
                "payload_checksum": catalog_response.get("checksum"),
                "dry_run": self.dry_run,
                "relevant_datasets": []
            }

        datasets = catalog_response.get("raw_payload", [])
        if not isinstance(datasets, list):
            datasets = []

        total_datasets = len(datasets)
        total_distributions = 0
        relevant_datasets = []

        for d in datasets:
            if not isinstance(d, dict):
                continue

            identifier = d.get("identifier") or d.get("id") or "unknown_id"
            title = d.get("title") or ""
            desc = d.get("description") or ""

            # Standardize keywords
            kw_raw = d.get("keyword", [])
            if isinstance(kw_raw, list):
                kw_str = " ".join([str(k) for k in kw_raw])
            else:
                kw_str = str(kw_raw)

            combined_text = f"{title} {desc} {kw_str}".lower()

            # Distributions parsing
            raw_dists = d.get("distribution", [])
            if not isinstance(raw_dists, list):
                raw_dists = []
            
            total_distributions += len(raw_dists)

            parsed_dists = []
            for dist in raw_dists:
                if not isinstance(dist, dict):
                    continue
                
                dist_data = dist.get("data", {}) if isinstance(dist.get("data"), dict) else dist
                parsed_dists.append({
                    "identifier": dist.get("identifier") or dist_data.get("identifier"),
                    "title": dist_data.get("title") or dist.get("title") or title,
                    "format": dist_data.get("format") or dist.get("format"),
                    "downloadURL": dist_data.get("downloadURL") or dist.get("downloadURL") or dist_data.get("accessURL")
                })

            # Check keyword match
            matched_kws = [term for term in self.RELEVANT_KEYWORDS if term in combined_text]

            # Filter out non-infrastructure datasets that match generic terms (e.g., drug licenses)
            is_infra_relevant = False
            if any(term in combined_text for term in ["road", "roads", "highway", "bridge", "flyover", "infrastructure", "r&b", "panchayat raj", "ghmc", "hmda", "construction", "transport"]):
                is_infra_relevant = True
            elif "works" in combined_text and any(term in combined_text for term in ["mission kakatiya", "drainage", "water works", "building"]):
                is_infra_relevant = True

            if is_infra_relevant:
                publisher_info = d.get("publisher")
                publisher_name = None
                if isinstance(publisher_info, dict):
                    publisher_name = publisher_info.get("data", {}).get("name") or publisher_info.get("name")
                else:
                    publisher_name = str(publisher_info) if publisher_info else "Government of Telangana"

                relevant_datasets.append({
                    "identifier": identifier,
                    "title": title,
                    "description": desc[:300] + "..." if len(desc) > 300 else desc,
                    "publisher": publisher_name,
                    "modified": d.get("modified"),
                    "source_url": d.get("url") or f"https://data.telangana.gov.in/dataset/{identifier}",
                    "matched_keywords": matched_kws,
                    "distribution_count": len(parsed_dists),
                    "distributions": parsed_dists
                })

        return {
            "source_name": self.source_name,
            "base_url": self.base_url,
            "api_reachable": True,
            "api_status_code": 200,
            "retrieved_at": catalog_response.get("retrieved_at"),
            "total_datasets_discovered": total_datasets,
            "total_distributions_discovered": total_distributions,
            "relevant_datasets_count": len(relevant_datasets),
            "payload_checksum": catalog_response.get("checksum"),
            "safe_discovery_mode": self.dry_run,
            "production_db_mutation_count": 0,
            "relevant_datasets": relevant_datasets
        }

    def run_safe_discovery(self, output_path: str = "data/live_discovery/telangana_open_data_catalog.json") -> Dict[str, Any]:
        """
        Executes end-to-end safe discovery flow without database mutations,
        and saves catalog metadata to output path.
        """
        logger.info("=== Starting Safe Discovery for Telangana Open Data Portal ===")
        raw_catalog = self.fetch_dataset_catalog()
        summary = self.discover_and_classify(raw_catalog)

        # Ensure output directory exists
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Discovery catalog saved to {out_file.resolve()}")
        logger.info(f"Total Datasets Discovered: {summary['total_datasets_discovered']}")
        logger.info(f"Total Distributions Discovered: {summary['total_distributions_discovered']}")
        logger.info(f"Relevant Road/Infrastructure Datasets: {summary['relevant_datasets_count']}")
        logger.info(f"Payload SHA-256 Checksum: {summary['payload_checksum']}")
        logger.info("=== Safe Discovery Execution Complete (Production DB Mutations: 0) ===")
        return summary

if __name__ == "__main__":
    collector = TelanganaOpenDataCollector(dry_run=True)
    collector.run_safe_discovery()
