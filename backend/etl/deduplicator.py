from typing import Dict, Any, Set, Tuple

class ETLDeduplicator:
    """
    Deterministic deduplication for procurement records.
    Generates exact and fuzzy deduplication keys:
    1. Tender ID
    2. Tender Reference Number
    3. Normalized Title + Organisation + Date
    """
    def __init__(self):
        self.seen_tender_ids: Set[str] = set()
        self.seen_ref_nos: Set[str] = set()
        self.seen_title_org_keys: Set[str] = set()

    def process(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Returns (is_duplicate, deduplication_key)
        """
        tender_id = record.get("tender_id")
        ref_no = record.get("tender_reference_number")
        title = (record.get("title") or "").strip().upper()
        org = (record.get("organisation") or "").strip().upper()
        aoc_date = str(record.get("aoc_date") or "")

        # 1. Exact Tender ID Check
        if tender_id and tender_id in self.seen_tender_ids:
            return True, f"EXACT_TENDER_ID_{tender_id}"
        if tender_id:
            self.seen_tender_ids.add(tender_id)

        # 2. Exact Reference Number Check
        if ref_no and ref_no != "NOT_AVAILABLE" and ref_no in self.seen_ref_nos:
            return True, f"EXACT_REF_NO_{ref_no}"
        if ref_no and ref_no != "NOT_AVAILABLE":
            self.seen_ref_nos.add(ref_no)

        # 3. Title + Organisation + Date Fuzzy Key
        composite_key = f"{title[:40]}_{org[:30]}_{aoc_date}"
        if composite_key in self.seen_title_org_keys:
            return True, f"COMPOSITE_TITLE_ORG_DATE_{composite_key}"
        self.seen_title_org_keys.add(composite_key)

        return False, "UNIQUE"
