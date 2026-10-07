from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseCollector(ABC):
    """
    Abstract base class for all data collectors.
    Ensures consistent interface for collecting, normalizing, and reporting source metadata.
    """
    def __init__(self, source_name: str, source_type: str, base_url: str):
        self.source_name = source_name
        self.source_type = source_type
        self.base_url = base_url

    @abstractmethod
    async def fetch_records(self, query: str | None = None) -> List[Dict[str, Any]]:
        """Fetch raw data records from external service."""
        pass

    @abstractmethod
    def normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize external schema to internal model schema."""
        pass
