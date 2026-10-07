import os
import secrets
import hashlib
import hmac
import base64
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from backend.auth.schemas import UserRole, TokenData
from backend.core.config import settings

logger = logging.getLogger(__name__)

# JWT Secret & Expiration configuration
JWT_SECRET = os.getenv("JWT_SECRET") or getattr(settings, "JWT_SECRET", None) or getattr(settings, "SECRET_KEY", None) or "tg_road_intel_production_jwt_secret_2026_super_secure"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440")) # Default 24 hours


class AuthService:
    """
    Secure password hashing using PBKDF2-HMAC-SHA256 (100,000 iterations)
    and HMAC-SHA256 JWT access token generation & verification.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes plaintext password using PBKDF2-HMAC-SHA256 with random salt."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()
        return f"pbkdf2_sha256${salt}${pwd_hash}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies plaintext password against stored salt and hash."""
        if not hashed_password or not hashed_password.startswith("pbkdf2_sha256$"):
            return False
        try:
            _, salt, stored_hash = hashed_password.split("$")
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                100000
            ).hex()
            return hmac.compare_digest(stored_hash, computed_hash)
        except Exception as e:
            logger.warning(f"Error verifying password: {e}")
            return False

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    @staticmethod
    def _base64url_decode(data_str: str) -> bytes:
        padding = '=' * (4 - (len(data_str) % 4))
        return base64.urlsafe_b64decode((data_str + padding).encode('utf-8'))

    @classmethod
    def create_access_token(
        cls,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generates HS256 signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode["exp"] = int(expire.timestamp())
        to_encode["iat"] = int(datetime.now(timezone.utc).timestamp())

        header = {"alg": "HS256", "typ": "JWT"}
        
        encoded_header = cls._base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
        encoded_payload = cls._base64url_encode(json.dumps(to_encode, separators=(',', ':')).encode('utf-8'))
        
        signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
        encoded_signature = cls._base64url_encode(signature)

        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    @classmethod
    def decode_access_token(cls, token: str) -> Optional[TokenData]:
        """Validates signature, expiration, and extracts claims from HS256 JWT."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            encoded_header, encoded_payload, encoded_signature = parts
            signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
            
            expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
            actual_sig = cls._base64url_decode(encoded_signature)

            if not hmac.compare_digest(expected_sig, actual_sig):
                logger.warning("Invalid JWT signature")
                return None

            payload = json.loads(cls._base64url_decode(encoded_payload).decode('utf-8'))
            exp = payload.get("exp")
            if exp and datetime.now(timezone.utc).timestamp() > exp:
                logger.warning("Expired JWT token")
                return None

            return TokenData(
                user_id=payload.get("user_id"),
                username=payload.get("sub"),
                role=UserRole(payload.get("role")) if payload.get("role") else None
            )
        except Exception as e:
            logger.warning(f"Error decoding JWT token: {e}")
            return None
