from typing import Dict, Any

class ETLValidator:
    """
    Validates record completeness and assigns data quality status flags:
    - VALID: Complete record with tender ID, title/description, organisation, and contractor/AOC date.
    - INCOMPLETE: Missing non-critical metadata (e.g. missing contractor or exact value).
    - POSSIBLE_DUPLICATE: Flags records sharing title/organisation keys.
    - LOW_RELEVANCE: Low relevance rating category.
    """
    def validate_record(self, record: Dict[str, Any], is_duplicate: bool) -> str:
        tender_id = record.get("tender_id")
        title = record.get("title")
        org = record.get("organisation")
        relevance = record.get("relevance_rating")

        if is_duplicate:
            return "POSSIBLE_DUPLICATE"

        if relevance == "LOW_RELEVANCE":
            return "LOW_RELEVANCE"

        if not tender_id or not title or not org:
            return "INCOMPLETE"

        # Check contractor & value availability
        has_contractor = bool(record.get("original_contractor_name"))
        has_val = bool(record.get("awarded_value"))

        if has_contractor and has_val:
            return "VALID"

        return "INCOMPLETE"
