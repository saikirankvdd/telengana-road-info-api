import re
from typing import Dict, Any, Tuple

class ProjectClassifier:
    """
    Statewide Telangana road and infrastructure project classifier.
    Categorizes procurement records into 18 fine-grained infrastructure categories.
    """
    CATEGORY_PATTERNS = [
        ("ELEVATED_CORRIDOR", ["ELEVATED CORRIDOR", "ELEVATED HIGHWAY CORRIDOR"]),
        ("ELEVATED_ROAD", ["ELEVATED ROAD", "VIADUCT ROAD"]),
        ("GRADE_SEPARATOR", ["GRADE SEPARATOR", "GRADE SEPARATION"]),
        ("INTERCHANGE", ["INTERCHANGE", "JUNCTION INTERCHANGE"]),
        ("FLYOVER", ["FLYOVER"]),
        ("ROB", ["RAIL OVER BRIDGE", " R.O.B", " ROB ", "ROB/"]),
        ("RUB", ["RAIL UNDER BRIDGE", " R.U.B", " RUB ", "RUB/"]),
        ("BRIDGE", ["BRIDGE", "RIVER BRIDGE", "CAUSEWAY"]),
        ("UNDERPASS", ["UNDERPASS", "VEHICULAR UNDERPASS", "PEDESTRIAN UNDERPASS"]),
        ("OVERPASS", ["OVERPASS", "VEHICULAR OVERPASS"]),
        ("ROAD_WIDENING", ["ROAD WIDENING", "WIDENING OF ROAD", "FOUR LANING", "SIX LANING", "DUALLING"]),
        ("ROAD_DEVELOPMENT", ["ROAD DEVELOPMENT", "SRDP", "STRATEGIC ROAD", "CORRIDOR DEVELOPMENT", "ROAD IMPROVEMENT"]),
        ("HIGHWAY", ["NATIONAL HIGHWAY", "STATE HIGHWAY", "NH-", "SH-", "EXPRESSWAY", "OUTER RING ROAD", "ORR"]),
        ("ROAD", ["ROAD", "PAVEMENT", "BITUMINOUS", "CC ROAD", "CARRIAGEWAY", "STREET", "ASPHALT", "RESURFACING", "TAR ROAD"]),
        ("CORRIDOR", ["CORRIDOR", "RADIAL ROAD"]),
        ("OTHER_TRANSPORT_INFRASTRUCTURE", ["BUS BAY", "TRAFFIC SIGNAL", "FOOTPATH", "PEDESTRIAN", "TOLL PLAZA"]),
        ("OTHER_INFRASTRUCTURE", ["DRAINAGE", "CULVERT", "STORMWATER", "INFRASTRUCTURE", "CIVIL WORKS", "JUNCTION"])
    ]

    def classify(self, record: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Returns (category, relevance_rating, matching_reason)
        """
        title = (record.get("title") or "").upper()
        parsed = record.get("parsed_json", {})
        desc = (parsed.get("Tender Description") or parsed.get("Work Description") or "").upper()
        text = f"{title} {desc}"

        # Low relevance / non-civil supply filter
        low_keywords = ["MACHINING", "COMPUTERS", "STATIONERY", "UNIFORM", "CATERING", "SECURITY GUARD", "MEDICAL"]
        if any(kw in text for kw in low_keywords) and not any(kw in text for kw in ["ROAD", "BRIDGE", "FLYOVER"]):
            return "NOT_RELEVANT", "LOW_RELEVANCE", "Non-civil supply/maintenance work"

        for cat, keywords in self.CATEGORY_PATTERNS:
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", text) or kw in text:
                    relevance = "HIGH_RELEVANCE" if cat in [
                        "ROAD", "HIGHWAY", "FLYOVER", "GRADE_SEPARATOR", "BRIDGE", "ROB", "RUB",
                        "ELEVATED_CORRIDOR", "ELEVATED_ROAD", "ROAD_WIDENING", "ROAD_DEVELOPMENT",
                        "INTERCHANGE", "UNDERPASS", "OVERPASS", "CORRIDOR"
                    ] else "POSSIBLE_RELEVANCE"
                    return cat, relevance, f"Matched keyword '{kw}'"

        return "OTHER_INFRASTRUCTURE", "POSSIBLE_RELEVANCE", "General civil infrastructure record"
