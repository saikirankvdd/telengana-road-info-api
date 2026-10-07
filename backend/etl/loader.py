import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class HistoricalETLLoader:
    """
    Handles writing processed ETL records to preview files or PostgreSQL DB.
    In Phase 2 dry-run mode, PostgreSQL operations are strictly disabled.
    """
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def load_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Loads records into PostgreSQL or dry-run summary buffer.
        """
        if self.dry_run:
            logger.info(f"DRY RUN ENABLED: Skipping PostgreSQL import for {len(records)} records.")
            return {
                "status": "DRY_RUN",
                "processed_count": len(records),
                "db_inserted": 0,
                "db_updated": 0
            }

        # PostgreSQL import logic would go here in Phase 3 when DB loading is explicitly enabled
        raise NotImplementedError("Direct database loading is disabled during Phase 2 preview ETL.")
