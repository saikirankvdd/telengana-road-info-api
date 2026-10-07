import os
import json
import sqlite3
import logging
from typing import Iterator, Dict, Any, List, Optional
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

# Comprehensive list of Telangana location, district, city, organisation & infrastructure search patterns
TELANGANA_SQL_PATTERNS: List[str] = [
    "%TELANGANA%", "%HYDERABAD%", "%GHMC%", "%HMDA%", "%TSIIC%", "%WARANGAL%",
    "%NIZAMABAD%", "%KARIMNAGAR%", "%KHAMMAM%", "%RAMAGUNDAM%", "%MAHABUBNAGAR%",
    "%NALGONDA%", "%ADILABAD%", "%SURYAPET%", "%MIRYALAGUDA%", "%SERILINGAMPALLY%",
    "%GACHIBOWLI%", "%UPPAL%", "%KONDAPUR%", "%KUKATPALLY%", "%LB NAGAR%",
    "%SECUNDERABAD%", "%CYBERABAD%", "%BEGUMPET%", "%HAKIMPET%", "%MEDCHAL%",
    "%RANGAREDDY%", "%RANGA REDDY%", "%SANGAREDDY%", "%SANGA REDDY%", "%SIDDIPET%",
    "%JAGTIAL%", "%MANCHERIAL%", "%KOTHAGUDEM%", "%BHADRADRI%", "%WANAPARTHY%",
    "%NAGARKURNOOL%", "%GADWAL%", "%VIKARABAD%", "%MEDAK%", "%PEDDAPALLI%",
    "%MULUGU%", "%BHUPALPALLY%", "%ASIFABAD%", "%NARAYANPET%", "%KAMAREDDY%",
    "%JANGAON%", "%YADADRI%", "%BHONGIR%", "%RAJANNA%", "%SIRCILLA%",
    "%RO HYDERABAD%", "%NHAI HYDERABAD%", "%ROADS & BUILDINGS%", "%ROADS AND BUILDINGS%",
    "%R&B%", "%MAUD%", "%MA&UD%"
]

class HistoricalSourceReader:
    """
    Memory-safe, highly optimized reader for Hugging Face historical procurement dataset (fireboy21/tenders_aoc).
    Uses SQL pushdown filtering for all Telangana keywords and primary key details lookup.
    """
    def __init__(self, repo_id: str = "fireboy21/tenders_aoc", db_path: Optional[str] = None):
        self.repo_id = repo_id
        self.db_path = db_path

    def initialize(self) -> str:
        if self.db_path and os.path.exists(self.db_path):
            return self.db_path

        logger.info(f"Downloading/Locating historical SQLite database from Hugging Face ({self.repo_id})...")
        try:
            downloaded_path = str(hf_hub_download(self.repo_id, "aoc_tenders.db", repo_type="dataset"))
            self.db_path = downloaded_path
            logger.info(f"Database ready at path: {self.db_path} (Size: {os.path.getsize(self.db_path) / (1024*1024):.2f} MB)")
            return downloaded_path
        except Exception as e:
            logger.error(f"Failed to download/locate historical database from Hugging Face: {e}")
            raise FileNotFoundError(f"Could not initialize historical dataset from Hugging Face repo '{self.repo_id}': {e}") from e

    def stream_records(self, chunk_size: int = 5000) -> Iterator[List[Dict[str, Any]]]:
        """
        Streams records matching Telangana keywords directly from SQLite database.
        Runs in ~1-2 minutes instead of hours by avoiding full table scans.
        """
        db_path = self.initialize()

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build SQL WHERE clause with LIKE conditions for org_name and title
            where_clauses: List[str] = []
            params: List[str] = []
            for pat in TELANGANA_SQL_PATTERNS:
                where_clauses.append("org_name LIKE ? OR title LIKE ?")
                params.extend([pat, pat])

            where_stmt = " OR ".join(where_clauses)
            query_tenders = f"""
            SELECT internal_id, tender_id, ref_no, title, org_name, aoc_date, 
                   closing_date, year, detail_url
            FROM aoc_tenders
            WHERE {where_stmt}
            """
            
            logger.info("Executing optimized SQL pushdown query for Telangana procurement records...")
            cursor.execute(query_tenders, params)

            details_cursor = conn.cursor()

            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                
                chunk_records: List[Dict[str, Any]] = [dict(r) for r in rows]
                internal_ids: List[str] = [str(r["internal_id"]) for r in chunk_records if r.get("internal_id")]

                # Fetch details in safe sub-batches of 500 to avoid SQLite variable limit (999 max)
                details_map: Dict[str, Any] = {}
                if internal_ids:
                    sub_batch_size = 500
                    for i in range(0, len(internal_ids), sub_batch_size):
                        batch_ids = internal_ids[i:i + sub_batch_size]
                        placeholders = ",".join("?" for _ in batch_ids)
                        details_query = f"SELECT internal_id, details_json FROM aoc_details WHERE internal_id IN ({placeholders})"
                        try:
                            details_cursor.execute(details_query, batch_ids)
                            for d_row in details_cursor.fetchall():
                                details_map[str(d_row["internal_id"])] = d_row["details_json"]
                        except sqlite3.OperationalError as e:
                            logger.warning(f"Could not query aoc_details table for batch: {e}")

                # Merge details into record chunk
                chunk: List[Dict[str, Any]] = []
                for record in chunk_records:
                    rec_id = str(record.get("internal_id", ""))
                    d_json_str = details_map.get(rec_id)
                    parsed_json: Dict[str, Any] = {}
                    if d_json_str:
                        try:
                            parsed_json = json.loads(d_json_str) if isinstance(d_json_str, str) else d_json_str
                        except Exception:
                            parsed_json = {}
                    record["details_json"] = d_json_str
                    record["parsed_json"] = parsed_json
                    chunk.append(record)

                yield chunk
        finally:
            conn.close()

