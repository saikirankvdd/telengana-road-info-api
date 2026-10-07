import logging
import urllib.parse
from typing import List, Optional
from duckduckgo_search import DDGS
from backend.schemas.research import SourceModel, SourceType, AuthorityLevel

logger = logging.getLogger(__name__)

PRIMARY_DOMAINS = [
    "telangana.gov.in",
    "tender.telangana.gov.in",
    "tg.gov.in",
    "nhai.gov.in",
    "ghmc.gov.in",
    "hmda.gov.in",
    "cppp.gov.in",
    "eprocure.gov.in",
    "nic.in",
    "india.gov.in",
    "morth.nic.in"
]

SECONDARY_DOMAINS = [
    "thehindu.com",
    "timesofindia.indiatimes.com",
    "deccanchronicle.com",
    "telanganatoday.com",
    "financialexpress.com",
    "business-standard.com",
    "moneycontrol.com",
    "thehindubusinessline.com",
    "urban-transport-newspaper.com",
    "constructionweekonline.in",
    "metrorailnews.in",
    "indiatoday.in",
    "expressbuzz.com",
    "indianexpress.com"
]

def categorize_source(url: str, title: str) -> tuple[SourceType, AuthorityLevel]:
    """Categorizes a URL into SourceType and AuthorityLevel."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()

    if any(p_dom in domain for p_dom in PRIMARY_DOMAINS) or domain.endswith(".gov.in"):
        if "tender" in domain or "tender" in url.lower() or "procure" in url.lower():
            return SourceType.TENDER_PORTAL, AuthorityLevel.PRIMARY
        if "go" in url.lower() or "order" in url.lower() or "gazette" in url.lower():
            return SourceType.GOVERNMENT_ORDER, AuthorityLevel.PRIMARY
        return SourceType.GOVERNMENT_PORTAL, AuthorityLevel.PRIMARY

    if any(s_dom in domain for s_dom in SECONDARY_DOMAINS):
        return SourceType.NEWS_MEDIA, AuthorityLevel.SECONDARY

    if "wikipedia.org" in domain or "researchgate.net" in domain:
        return SourceType.RESEARCH, AuthorityLevel.TERTIARY

    return SourceType.OTHER, AuthorityLevel.TERTIARY

class LiveSearchProvider:
    def __init__(self, max_results_per_query: int = 5):
        self.max_results_per_query = max_results_per_query

    def generate_queries(self, project_name: str) -> List[str]:
        return [
            f'"{project_name}" Telangana tender R&B',
            f'"{project_name}" Telangana government order GO cost',
            f'"{project_name}" contractor tender ID cost length',
            f'"{project_name}" NHAI HMDA GHMC Telangana'
        ]

    def search(self, project_name: str, max_total_results: int = 10) -> List[SourceModel]:
        queries = self.generate_queries(project_name)
        seen_urls = set()
        sources: List[SourceModel] = []

        try:
            ddgs = DDGS()
            for q in queries:
                if len(sources) >= max_total_results:
                    break
                try:
                    results = ddgs.text(q, max_results=self.max_results_per_query)
                    if not results:
                        continue

                    for item in results:
                        url = item.get("href") or item.get("link")
                        if not url or url in seen_urls:
                            continue

                        seen_urls.add(url)
                        title = item.get("title") or "Untitled Document"
                        snippet = item.get("body") or item.get("snippet") or ""

                        stype, auth_level = categorize_source(url, title)

                        sources.append(
                            SourceModel(
                                source_id=f"src_{len(sources)+1:03d}",
                                source_url=url,
                                source_name=title[:120],
                                source_type=stype,
                                publisher=urllib.parse.urlparse(url).netloc,
                                title=title,
                                evidence_text=snippet,
                                authority_level=auth_level
                            )
                        )
                except Exception as query_err:
                    logger.warning(f"Search query failed for '{q}': {query_err}")
                    continue

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")

        # Sort sources by authority level (PRIMARY > SECONDARY > TERTIARY)
        level_order = {AuthorityLevel.PRIMARY: 0, AuthorityLevel.SECONDARY: 1, AuthorityLevel.TERTIARY: 2}
        sources.sort(key=lambda s: level_order.get(s.authority_level, 3))

        return sources[:max_total_results]
