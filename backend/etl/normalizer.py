import re
from typing import Dict, Any, Optional

TELANGANA_DISTRICTS = [
    "ADILABAD", "BHADRADRI KOTHAGUDEM", "KOTHAGUDEM", "HYDERABAD", "JAGTIAL",
    "JANGAON", "JAYASHANKAR BHUPALPALLY", "BHUPALPALLY", "JOGULAMBA GADWAL", "GADWAL",
    "KAMAREDDY", "KARIMNAGAR", "KHAMMAM", "KUMURAM BHEEM ASIFABAD", "ASIFABAD",
    "MAHABUBNAGAR", "MAHABUBABAD", "MANCHERIAL", "MEDAK", "MEDCHAL-MALKAJGIRI",
    "MEDCHAL", "MALKAJGIRI", "MULUGU", "NAGARKURNOOL", "NALGONDA", "NARAYANPET",
    "NIZAMABAD", "PEDDAPALLI", "RAJANNA SIRCILLA", "SIRCILLA", "RANGAREDDY",
    "RANGA REDDY", "SANGAREDDY", "SANGA REDDY", "SIDDIPET", "SURYAPET",
    "VIKARABAD", "WANAPARTHY", "YADADRI BHONGIR", "BHONGIR", "WARANGAL", "HANUMAKONDA"
]

TELANGANA_CITIES_MUNICIPALITIES = [
    "HYDERABAD", "GHMC", "WARANGAL", "GWMC", "NIZAMABAD", "KARIMNAGAR",
    "KHAMMAM", "RAMAGUNDAM", "MAHABUBNAGAR", "NALGONDA", "ADILABAD",
    "SURYAPET", "MIRYALAGUDA", "SERILINGAMPALLY", "GACHIBOWLI", "UPPAL",
    "KONDAPUR", "KUKATPALLY", "LB NAGAR", "SECUNDERABAD", "CYBERABAD",
    "BEGUMPET", "HAKIMPET", "KOTHAGUDEM", "MANCHERIAL"
]

class ETLNormalizer:
    """
    Normalizes raw procurement records into clean statewide intermediate schemas.
    Preserves original source fields while generating deterministic normalized keys.
    """
    def normalize_contractor_name(self, raw_name: Optional[str]) -> Optional[str]:
        if not raw_name or raw_name == "NOT_AVAILABLE":
            return None
        name = raw_name.strip()
        normalized = re.sub(r"^(M/S\s+|M/S\.\s+)", "", name, flags=re.IGNORECASE)
        normalized = re.sub(r"\b(PVT|PRIVATE|LTD|LIMITED|INC|CORP|CONSTRUCTIONS?|INFRASTRUCTURE|INFRA)\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = " ".join(normalized.split()).upper()
        return normalized if normalized else name.upper()

    def extract_district(self, text: str) -> Optional[str]:
        text_upper = text.upper()
        for d in TELANGANA_DISTRICTS:
            if re.search(rf"\b{re.escape(d)}\b", text_upper):
                return d
        return None

    def extract_city(self, text: str) -> Optional[str]:
        text_upper = text.upper()
        for c in TELANGANA_CITIES_MUNICIPALITIES:
            if re.search(rf"\b{re.escape(c)}\b", text_upper):
                return c
        return None

    def generate_project_candidate_key(self, title: str, org: str, district: Optional[str]) -> str:
        clean_title = re.sub(r"[^\w\s]", "", title.upper())
        words = [w for w in clean_title.split() if len(w) > 3][:5]
        base_name = "_".join(words)
        loc_tag = district or "TELANGANA"
        org_tag = (org or "GOVT").upper()[:15].replace(" ", "_")
        return f"PROJ_{loc_tag}_{org_tag}_{base_name}"

    def normalize_record(self, raw: Dict[str, Any], category: str, relevance: str, reason: str) -> Dict[str, Any]:
        parsed = raw.get("parsed_json", {})
        
        orig_contractor = parsed.get("Name of the selected bidder(s)") or None
        norm_contractor = self.normalize_contractor_name(orig_contractor)

        raw_val = parsed.get("Contract Value") or None
        awarded_val = None
        if raw_val:
            try:
                clean_val = str(raw_val).replace("₹", "").replace(",", "").strip()
                awarded_val = float(clean_val)
            except Exception:
                pass

        completion_period = parsed.get("Date of Completion/Completion Period in Days") or None

        title = raw.get("title") or parsed.get("Tender Title") or ""
        desc = parsed.get("Tender Description") or parsed.get("Work Description") or title
        org = raw.get("org_name") or parsed.get("Organisation Name") or ""
        dept = parsed.get("Department") or org
        address = parsed.get("Address of the selected bidder(s)") or parsed.get("Location") or ""

        search_text = f"{title} {desc} {org} {address}"
        district = self.extract_district(search_text)
        city = self.extract_city(search_text)
        project_key = self.generate_project_candidate_key(title, org, district)

        return {
            "source_name": "fireboy21/tenders_aoc",
            "source_type": "HISTORICAL_HF_DATASET",
            "source_record_id": raw.get("internal_id"),
            "internal_id": raw.get("internal_id"),
            "tender_id": raw.get("tender_id"),
            "tender_reference_number": raw.get("ref_no") or parsed.get("Tender Ref. No."),
            "project_name": title,
            "work_description": desc,
            "project_candidate_key": project_key,
            "organisation": org,
            "department": dept,
            "executing_authority": dept or org,
            "state": "Telangana",
            "district": district if district else "NOT_FOUND",
            "city": city if city else "NOT_FOUND",
            "municipality": city if city in ["GHMC", "GWMC", "HYDERABAD", "WARANGAL", "NIZAMABAD", "KARIMNAGAR", "KHAMMAM", "RAMAGUNDAM"] else "NOT_FOUND",
            "locality": city if city and city not in ["TELANGANA", "HYDERABAD"] else "NOT_FOUND",
            "location_text": address or f"{city or 'Telangana'}, Telangana",
            "latitude": None,
            "longitude": None,
            "tender_title": title,
            "tender_publication_date": parsed.get("Published Date") or parsed.get("ePublished Date"),
            "tender_closing_date": raw.get("closing_date") or parsed.get("Bid Submission End Date"),
            "aoc_date": raw.get("aoc_date") or parsed.get("Contract Date"),
            "original_contractor_name": orig_contractor,
            "normalized_contractor_name": norm_contractor,
            "contractor": norm_contractor,
            "selected_bidder": orig_contractor,
            "awarded_value": awarded_val,
            "contract_value": awarded_val,
            "completion_period": completion_period,
            "source_url": raw.get("detail_url") or parsed.get("Tender Document"),
            "retrieved_at": "2026-10-03T00:00:00Z",
            "category": category,
            "relevance_rating": relevance,
            "matching_reason": reason,
        }
