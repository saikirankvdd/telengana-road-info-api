import os
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.core.config import settings
from backend.schemas.research import SourceModel

logger = logging.getLogger(__name__)

class RawExtractedField(BaseModel):
    value: Optional[Any] = Field(default=None, description="Exact value extracted from evidence, or null if not found")
    evidence_snippet: Optional[str] = Field(default=None, description="Verbatim text snippet from evidence supporting value")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    page: Optional[int] = Field(default=None, description="Page number where evidence was located if document has page numbers")

class GeminiExtractionResponse(BaseModel):
    project_name: Optional[RawExtractedField] = None
    project_id: Optional[RawExtractedField] = None
    government_project_id: Optional[RawExtractedField] = None

    tender_id: Optional[RawExtractedField] = None
    reference_number: Optional[RawExtractedField] = None
    tender_reference: Optional[RawExtractedField] = None
    tender_publication_date: Optional[RawExtractedField] = None
    publication_date: Optional[RawExtractedField] = None
    tender_closing_date: Optional[RawExtractedField] = None
    submission_deadline: Optional[RawExtractedField] = None
    award_date: Optional[RawExtractedField] = None
    awarded_date: Optional[RawExtractedField] = None

    government_order_number: Optional[RawExtractedField] = None
    government_order_date: Optional[RawExtractedField] = None

    authority: Optional[RawExtractedField] = None
    department: Optional[RawExtractedField] = None

    contractor: Optional[RawExtractedField] = None
    contractor_registration: Optional[RawExtractedField] = None

    estimated_cost: Optional[RawExtractedField] = None
    tender_value: Optional[RawExtractedField] = None
    awarded_cost: Optional[RawExtractedField] = None

    project_length: Optional[RawExtractedField] = None
    road_length_km: Optional[RawExtractedField] = None
    lanes: Optional[RawExtractedField] = None
    number_of_lanes: Optional[RawExtractedField] = None

    location: Optional[RawExtractedField] = None
    district: Optional[RawExtractedField] = None
    mandal: Optional[RawExtractedField] = None
    constituency: Optional[RawExtractedField] = None
    start_point: Optional[RawExtractedField] = None
    end_point: Optional[RawExtractedField] = None
    start_chainage: Optional[RawExtractedField] = None
    end_chainage: Optional[RawExtractedField] = None

    latitude: Optional[RawExtractedField] = None
    longitude: Optional[RawExtractedField] = None

    status: Optional[RawExtractedField] = None
    completion_date: Optional[RawExtractedField] = None
    contract_start_date: Optional[RawExtractedField] = None
    contract_end_date: Optional[RawExtractedField] = None
    work_order_number: Optional[RawExtractedField] = None
    funding_agency: Optional[RawExtractedField] = None
    road_number: Optional[RawExtractedField] = None
    dpr_reference: Optional[RawExtractedField] = None

    physical_progress: Optional[RawExtractedField] = None
    financial_progress: Optional[RawExtractedField] = None
    delay_reason: Optional[RawExtractedField] = None
    execution_mode: Optional[RawExtractedField] = None
    road_structure: Optional[RawExtractedField] = None
    foundation: Optional[RawExtractedField] = None
    viaduct_length: Optional[RawExtractedField] = None

EXTRACTION_SYSTEM_INSTRUCTION = (
    "You are an evidence extraction engine. Use ONLY the supplied source evidence text.\n"
    "CRITICAL MANDATORY RULES:\n"
    "1. Do NOT use your prior knowledge to fill missing values.\n"
    "2. Do NOT infer or guess unsupported values.\n"
    "3. Every extracted non-null value MUST point to supporting evidence text.\n"
    "4. If page headers like [Page X] appear in the text, extract X as the page number.\n"
    "5. If the evidence text does not contain a value for a field, return null for that field.\n"
    "6. Do NOT invent URLs or reference numbers.\n"
    "7. Output valid JSON matching the exact schema."
)

class GeminiExtractorService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini SDK client: {e}")

    def extract_from_evidence(
        self,
        project_name_query: str,
        source: SourceModel,
        raw_content: str,
        model_name: str = "gemini-3.8-flash"
    ) -> Dict[str, RawExtractedField]:
        if not raw_content or not raw_content.strip():
            return {}

        models_to_try = [model_name, "gemini-3.5-flash", "gemini-3.5-flash-lite"]
        # Remove duplicates preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        prompt = (
            f"TARGET PROJECT NAME: {project_name_query}\n"
            f"SOURCE URL: {source.source_url or 'N/A'}\n"
            f"SOURCE NAME: {source.source_name}\n"
            f"AUTHORITY LEVEL: {source.authority_level}\n"
            f"SOURCE EVIDENCE CONTENT:\n---\n{raw_content}\n---\n\n"
            "Extract all project fields supported by the evidence content above."
        )

        if self._client:
            for m in models_to_try:
                try:
                    response = self._client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config={
                            "system_instruction": EXTRACTION_SYSTEM_INSTRUCTION,
                            "response_mime_type": "application/json",
                            "response_schema": GeminiExtractionResponse
                        }
                    )

                    if response and response.text:
                        parsed_json = json.loads(response.text)
                        results = {}
                        for field, data in parsed_json.items():
                            if isinstance(data, dict):
                                results[field] = RawExtractedField(**data)
                        if results:
                            return results
                except Exception as e:
                    logger.warning(f"Gemini model '{m}' extraction attempt error: {e}")
                    continue

        # Heuristic fallback if LLM client is unavailable or all models exhausted quota
        logger.info(f"Using rule-based evidence extraction fallback for source '{source.source_name}'")
        return self._fallback_heuristic_extraction(project_name_query, raw_content)

    def _fallback_heuristic_extraction(self, query: str, content: str) -> Dict[str, RawExtractedField]:
        import re
        results: Dict[str, RawExtractedField] = {}

        # If project query is not mentioned in content (or query is fake/unmatched), skip extracting facts from generic page content
        query_words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 3]
        query_mentioned = query.lower() in content.lower() or (query_words and any(w in content.lower() for w in query_words))

        if not query_mentioned:
            return {}

        # 1. Project Name
        if query.lower() in content.lower():
            results["project_name"] = RawExtractedField(
                value=query,
                evidence_snippet=f"Found mentioned project '{query}' in source content",
                confidence=0.85
            )

        # 2. Financials (Cost in Crores or INR)
        cost_match = re.search(r'(?:rs\.?|inr|cost|amount|budget|est\.?|estimated|val\.?)\s*(?:of|is|:)?\s*(?:rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lakh|million)?', content, re.IGNORECASE)
        if cost_match:
            try:
                val_num = float(cost_match.group(1).replace(",", ""))
                unit = (cost_match.group(2) or "").lower()
                if "lakh" in unit:
                    val_num = round(val_num / 100.0, 2)
                results["estimated_cost"] = RawExtractedField(
                    value=val_num,
                    evidence_snippet=cost_match.group(0)[:150],
                    confidence=0.80
                )
            except Exception:
                pass

        # 3. Road Length
        length_match = re.search(r'([\d.]+)\s*(?:km|kms|kilometers|kilometer)', content, re.IGNORECASE)
        if length_match:
            try:
                l_val = float(length_match.group(1))
                if 0.1 <= l_val <= 500.0:
                    results["road_length_km"] = RawExtractedField(
                        value=l_val,
                        evidence_snippet=length_match.group(0),
                        confidence=0.85
                    )
            except Exception:
                pass

        # 4. Tender ID / Reference (must contain digits!)
        tender_match = re.search(r'(?:tender\s*(?:id|ref|no|number))\s*[:#-]?\s*([A-Za-z0-9/\-_]*\d+[A-Za-z0-9/\-_]*)', content, re.IGNORECASE)
        if tender_match:
            results["tender_id"] = RawExtractedField(
                value=tender_match.group(1),
                evidence_snippet=tender_match.group(0),
                confidence=0.80
            )

        # 5. Authority
        for auth_kw in ["NHAI", "HMDA", "GHMC", "R&B", "TSIIC", "R&B Department", "Government of Telangana", "Ministry of Road Transport and Highways"]:
            if auth_kw.lower() in content.lower():
                results["authority"] = RawExtractedField(
                    value=auth_kw,
                    evidence_snippet=f"Authority '{auth_kw}' identified in source evidence",
                    confidence=0.85
                )
                break

        # 6. District
        districts = ["Hyderabad", "Medchal", "Ranga Reddy", "Sangareddy", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Medak", "Nalgonda", "Siddipet"]
        for d in districts:
            if d.lower() in content.lower():
                results["district"] = RawExtractedField(
                    value=d,
                    evidence_snippet=f"District '{d}' identified in evidence text",
                    confidence=0.80
                )
                break

        return results

