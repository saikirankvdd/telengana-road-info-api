import re
from typing import Dict, Any

# Keywords identifying Telangana state procurement organisations & locations
TELANGANA_KEYWORDS = [
    "TELANGANA", "TG ", "TS ", "GHMC", "HMDA", "TSIIC", "HYDERABAD",
    "WARANGAL", "NIZAMABAD", "KARIMNAGAR", "KHAMMAM", "RAMAGUNDAM",
    "MAHABUBNAGAR", "NALGONDA", "ADILABAD", "SURYAPET", "MIRYALAGUDA",
    "SERILINGAMPALLY", "GACHIBOWLI", "UPPAL", "KONDAPUR", "KUKATPALLY",
    "LB NAGAR", "SECUNDERABAD", "CYBERABAD", "BEGUMPET", "HAKIMPET"
]

TELANGANA_ORGANISATIONS = [
    "RO HYDERABAD", "NHAI HYDERABAD", "TELANGANA ROADS & BUILDINGS",
    "GREATER HYDERABAD MUNICIPAL CORPORATION", "HYDERABAD METROPOLITAN DEVELOPMENT AUTHORITY",
    "TELANGANA STATE INDUSTRIAL INFRASTRUCTURE", "MAUD", "MA&UD"
]

class TelanganaFilter:
    """
    Evaluates whether a procurement record originates from Telangana state.
    Examines organisation name, department, title, address, and parsed JSON payload.
    """
    def is_telangana_record(self, record: Dict[str, Any]) -> bool:
        org_name = (record.get("org_name") or "").upper()
        title = (record.get("title") or "").upper()
        parsed_json = record.get("parsed_json", {})
        
        address = (parsed_json.get("Address of the selected bidder(s)") or "").upper()
        dept = (parsed_json.get("Department") or "").upper()
        desc = (parsed_json.get("Tender Description") or "").upper()

        text_block = f"{org_name} {title} {address} {dept} {desc}"

        # 1. Direct Organisation Match
        if any(org in text_block for org in TELANGANA_ORGANISATIONS):
            return True

        # 2. Keyword Match in Location/State/Org
        if any(re.search(rf"\b{kw}\b", text_block) for kw in TELANGANA_KEYWORDS):
            return True

        return False
