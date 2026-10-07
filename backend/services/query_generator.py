import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SourceQueryGenerator:
    """
    Dynamically generates source-specific and deep research queries for a project request.
    Extracts road numbers, locations, authorities, tender references, and infrastructure keywords.
    """
    def generate_queries(
        self,
        project_name: str,
        context: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None
    ) -> List[str]:
        queries: List[str] = [project_name]

        # 1. Broad region/state query
        if "telangana" not in project_name.lower():
            queries.append(f"{project_name} Telangana")

        # 2. Extract road number (e.g. NH-163, NH163, SH-1, ORR)
        nh_match = re.search(r'\b(NH[-\s]?\d+|SH[-\s]?\d+|ORR)\b', project_name, re.IGNORECASE)
        if nh_match:
            road_num = nh_match.group(1).upper()
            queries.append(f"{project_name} {road_num}")
            queries.append(f"{road_num} Telangana")

        # 3. Dynamic infrastructure / document search variants
        queries.extend([
            f"{project_name} tender",
            f"{project_name} contractor",
            f"{project_name} project cost",
            f"{project_name} progress",
            f"{project_name} completion date",
            f"{project_name} Telangana R&B",
            f"{project_name} NHAI",
            f"{project_name} government order",
            f"{project_name} DPR",
            f"{project_name} PDF",
            f"{project_name} DPR report"
        ])

        # 4. Context-based query expansions
        if context:
            if context.get("district"):
                queries.append(f"{project_name} {context['district']}")
            if context.get("authority"):
                queries.append(f"{project_name} {context['authority']}")
            if context.get("tender_reference"):
                queries.append(context["tender_reference"])
            if context.get("government_project_id"):
                queries.append(context["government_project_id"])

        # 5. Source-specific query tailoring
        if source_id == "telangana_go":
            queries.append(f"{project_name} Government Order")
            queries.append(f"{project_name} G.O. Ms. No.")
        elif source_id == "cppp_eproc":
            queries.append(f"{project_name} tender site:eprocure.gov.in")
            queries.append(f"{project_name} CPPP")
        elif source_id == "nhai":
            queries.append(f"{project_name} NHAI project site:nhai.gov.in")
        elif source_id == "morth":
            queries.append(f"{project_name} site:morth.nic.in")
        elif source_id == "ghmc":
            queries.append(f"{project_name} GHMC road flyover")
        elif source_id == "hmda":
            queries.append(f"{project_name} HMDA infrastructure")

        # Deduplicate while preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            norm_q = q.strip().lower()
            if norm_q not in seen:
                seen.add(norm_q)
                unique_queries.append(q)

        return unique_queries
