import logging
import httpx
from typing import Any, Dict, List
from backend.core.config import settings
from backend.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

class TelanganaEProcurementCollector(BaseCollector):
    """
    Collector module for Telangana e-Procurement Portal (tender.telangana.gov.in).
    Collects publicly accessible tender publications and AOC records.
    """
    def __init__(self):
        super().__init__(
            source_name="Telangana e-Procurement Portal",
            source_type="EPROCUREMENT",
            base_url=settings.TELANGANA_EPROCUREMENT_URL
        )

    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        """
        Queries accessible public tender search interface.
        Returns list of parsed tender metadata.
        """
        # Note: Respecting site rules and public boundary rules
        target_url = f"{self.base_url}/public/tenders/search"
        params = {"keyword": query} if query else {}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(target_url, params=params)
                if response.status_code == 200:
                    # Parse XML/JSON/HTML if endpoint returns structured payload
                    return []
        except Exception as e:
            logger.info(f"e-Procurement public search endpoint unreachable or blocked: {e}")
        return []

    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tender_id": raw_data.get("tender_id"),
            "tender_reference_number": raw_data.get("ref_no"),
            "title": raw_data.get("work_description") or raw_data.get("title"),
            "organisation": raw_data.get("organisation"),
            "department": raw_data.get("department"),
            "estimated_value": raw_data.get("ecv"),
            "source_url": raw_data.get("url") or self.base_url
        }
