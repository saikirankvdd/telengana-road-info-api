import logging
import hashlib
import httpx
from typing import Any, Dict, List
from backend.core.config import settings
from backend.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

class TelanganaOpenDataCollector(BaseCollector):
    """
    Collector for Telangana Open Data Portal (data.telangana.gov.in).
    Queries official DKAN 2.0 Metastore API for road infrastructure & government works datasets.
    """
    METASTORE_URL = "https://data.telangana.gov.in/api/1/metastore/schemas/dataset/items"

    def __init__(self):
        super().__init__(
            source_name="Telangana Open Data Portal",
            source_type="TELANGANA_OPEN_DATA",
            base_url=self.METASTORE_URL
        )
        self.user_agent = "TelanganaRoadIntelAPI/1.0 (Safe Discovery)"

    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        """
        Queries DKAN metastore items endpoint. Returns raw dataset metadata items.
        """
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.METASTORE_URL, headers=headers)
                if response.status_code == 200:
                    datasets = response.json()
                    if isinstance(datasets, list):
                        if not query:
                            return datasets
                        query_lower = query.lower()
                        return [
                            d for d in datasets
                            if isinstance(d, dict) and (
                                query_lower in (d.get("title") or "").lower() or
                                query_lower in (d.get("description") or "").lower()
                            )
                        ]
        except Exception as e:
            logger.warning(f"Telangana Open Data Metastore API connection error: {e}")
        return []

    def compute_checksum(self, raw_data: Any) -> str:
        """Computes SHA-256 checksum of raw payload."""
        import json
        encoded = json.dumps(raw_data, sort_keys=True).encode("utf-8") if isinstance(raw_data, (dict, list)) else str(raw_data).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        dists = raw_data.get("distribution", []) if isinstance(raw_data.get("distribution"), list) else []
        publisher_info = raw_data.get("publisher", {})
        publisher_name = publisher_info.get("data", {}).get("name") if isinstance(publisher_info, dict) else str(publisher_info)

        return {
            "external_id": str(raw_data.get("identifier") or raw_data.get("id")),
            "project_name": raw_data.get("title"),
            "description": raw_data.get("description"),
            "department": publisher_name,
            "modified_date": raw_data.get("modified"),
            "distribution_count": len(dists),
            "source_url": raw_data.get("url") or f"https://data.telangana.gov.in/dataset/{raw_data.get('identifier')}"
        }
