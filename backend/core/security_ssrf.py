import ipaddress
import socket
import logging
from urllib.parse import urlparse
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

# Permitted schemes
ALLOWED_SCHEMES = {"http", "https"}

# Cloud metadata and special IP addresses
BLOCKED_IP_STRINGS = {
    "169.254.169.254", # AWS / GCP / Azure metadata
    "169.254.169.254.xip.io",
    "metadata.google.internal"
}


class SSRFValidationError(ValueError):
    """Raised when an outbound URL violates SSRF safety boundaries."""
    pass


class SSRFProtector:
    """
    Enforces SSRF, DNS Rebinding, Scheme Validation, and Private IP Filter rules.
    """

    @staticmethod
    def is_ip_private_or_loopback(ip_str: str) -> bool:
        """Evaluates whether an IP address belongs to loopback, private, or link-local ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            return (
                ip_obj.is_loopback or
                ip_obj.is_private or
                ip_obj.is_link_local or
                ip_obj.is_multicast or
                ip_obj.is_reserved or
                ip_obj.is_unspecified
            )
        except ValueError:
            return False

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, str, str]:
        """
        Validates URL scheme, resolves hostname, and checks resolved IP against SSRF boundaries.
        Returns: (is_valid, parsed_hostname, resolved_ip)
        Raises: SSRFValidationError if safety rules are violated.
        """
        if not url or not isinstance(url, str):
            raise SSRFValidationError("URL string cannot be empty")

        url_clean = url.strip()
        parsed = urlparse(url_clean)

        # 1. Scheme Validation
        scheme = parsed.scheme.lower() if parsed.scheme else ""
        if scheme not in ALLOWED_SCHEMES:
            raise SSRFValidationError(f"Invalid URL scheme '{scheme}'. Only http and https are permitted.")

        # 2. Hostname extraction
        hostname = parsed.hostname
        if not hostname:
            raise SSRFValidationError("URL lacks valid hostname")

        hostname_lower = hostname.lower()

        # Check explicit blocked hostname strings
        if hostname_lower in ("localhost", "0.0.0.0", "127.0.0.1", "::1") or hostname_lower in BLOCKED_IP_STRINGS:
            raise SSRFValidationError(f"Access to local or metadata destination '{hostname}' is blocked")

        # 3. DNS Resolution & Rebinding Check
        try:
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not resolved_ips:
                raise SSRFValidationError(f"Could not resolve hostname '{hostname}'")

            for entry in resolved_ips:
                ip_str = entry[4][0]
                if cls.is_ip_private_or_loopback(ip_str):
                    logger.warning(f"SSRF Protection blocked request to '{url}': Hostname '{hostname}' resolved to private IP '{ip_str}'")
                    raise SSRFValidationError(f"Destination hostname '{hostname}' resolves to private/internal IP '{ip_str}'")

            primary_ip = resolved_ips[0][4][0]
            return True, hostname, primary_ip
        except socket.gaierror as dns_err:
            raise SSRFValidationError(f"DNS resolution failed for hostname '{hostname}': {dns_err}")

    @classmethod
    def validate_redirect_target(cls, current_url: str, redirect_target: str) -> str:
        """
        Validates HTTP redirect target URL against SSRF rules before following redirect.
        """
        parsed_target = urlparse(redirect_target)
        if not parsed_target.scheme:
            # Relative redirect target
            base = urlparse(current_url)
            redirect_target = f"{base.scheme}://{base.netloc}{redirect_target}"

        cls.validate_url(redirect_target)
        return redirect_target
