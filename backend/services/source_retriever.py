import io
import logging
import httpx
from bs4 import BeautifulSoup
from typing import Optional
from backend.schemas.research import SourceModel

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 TelanganaRoadIntelligenceBot/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

class LiveSourceRetriever:
    def __init__(self, timeout_seconds: float = 8.0, max_content_length: int = 25000):
        self.timeout = timeout_seconds
        self.max_content_length = max_content_length

    def fetch_content(self, source: SourceModel) -> Optional[str]:
        if not source.source_url:
            return source.evidence_text

        # Safety Check: Do not attempt restricted portals requiring login/CAPTCHA
        restricted_indicators = ["captcha", "login", "auth", "session"]
        if any(ind in source.source_url.lower() for ind in restricted_indicators):
            logger.info(f"Skipping restricted URL {source.source_url}")
            return source.evidence_text

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
                verify=False  # Allow government portals with outdated self-signed SSL certs safely for research text
            ) as client:
                resp = client.get(source.source_url)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "").lower()
                    is_pdf = source.source_url.lower().endswith(".pdf") or "application/pdf" in content_type

                    if is_pdf:
                        return self.extract_pdf_text(resp.content, source)

                    html_content = resp.text
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Strip irrelevant tags
                    for element in soup(["script", "style", "nav", "footer", "header", "form", "iframe", "noscript"]):
                        element.decompose()

                    plain_text = soup.get_text(separator="\n")
                    # Clean up blank lines
                    lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
                    clean_text = "\n".join(lines)

                    if len(clean_text) > self.max_content_length:
                        clean_text = clean_text[:self.max_content_length] + "\n...[Truncated]"

                    return clean_text

        except Exception as e:
            logger.warning(f"Failed to fetch content from {source.source_url}: {e}")

        # Fallback to initial evidence snippet if full fetch fails
        return source.evidence_text

    def extract_pdf_text(self, pdf_bytes: bytes, source: SourceModel) -> str:
        """
        Extracts plain text from PDF bytes page by page, tagging each section with page numbers.
        """
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            page_texts = []
            for idx, page in enumerate(reader.pages, start=1):
                txt = page.extract_text() or ""
                if txt.strip():
                    page_texts.append(f"[Page {idx}]\n{txt.strip()}")

            full_pdf_text = "\n\n".join(page_texts)
            if len(full_pdf_text) > self.max_content_length:
                full_pdf_text = full_pdf_text[:self.max_content_length] + "\n...[Truncated]"

            logger.info(f"Successfully extracted {len(page_texts)} pages from PDF source {source.source_name}")
            return full_pdf_text
        except Exception as e:
            logger.warning(f"Failed to parse PDF from {source.source_url}: {e}")
            return source.evidence_text or ""
