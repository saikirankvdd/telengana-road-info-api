import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Patterns commonly present in prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|system)",
    r"reveal\s+(your\s+)?(system\s+prompt|secret|api\s+key)",
    r"disregard\s+(above|previous)\s+directions",
    r"you\s+are\s+now\s+a",
    r"override\s+system\s+instructions",
    r"call\s+this\s+url",
    r"return\s+this\s+fabricated\s+value",
    r"exec\s*\(",
    r"<script\b"
]


class PromptGuard:
    """
    Sanitizes untrusted webpage text before passing it to Gemini,
    neutralizing prompt injection attempts while preserving factual text.
    """

    @classmethod
    def sanitize_untrusted_text(cls, raw_text: str) -> Tuple[str, bool]:
        """
        Scans webpage text for prompt injection signatures.
        Returns: (sanitized_text, injection_detected_flag)
        """
        if not raw_text:
            return "", False

        text_str = str(raw_text)
        injection_found = False

        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text_str, re.IGNORECASE):
                injection_found = True
                logger.warning(f"PromptGuard detected potential prompt injection pattern '{pattern}' in untrusted text")
                # Redact matched prompt injection directive
                text_str = re.sub(pattern, "[REDACTED_PROMPT_INJECTION_DIRECTIVE]", text_str, flags=re.IGNORECASE)

        # Wrap untrusted text explicitly in XML data boundary tags
        guarded_text = f"<UNTRUSTED_EXTERNAL_WEBPAGE_DATA>\n{text_str}\n</UNTRUSTED_EXTERNAL_WEBPAGE_DATA>"
        return guarded_text, injection_found
