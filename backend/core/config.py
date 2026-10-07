from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Telangana Road & Project Intelligence API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./telangana_road_intel.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # External GIS & Government Service Endpoints
    TELANGANA_GIS_BASE_URL: str = "http://tracgis.telangana.gov.in/arcgis/rest/services"
    BHUVAN_GIS_BASE_URL: str = "https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms"
    OVERPASS_GIS_BASE_URL: str = "https://overpass-api.de/api/interpreter"
    TELANGANA_OPEN_DATA_BASE_URL: str = "https://data.telangana.gov.in/api/v1"
    DATA_GOV_API_KEY: str = ""
    TELANGANA_EPROCUREMENT_URL: str = "https://tender.telangana.gov.in"

    # Security & Production Limits
    API_KEY: str = "tg_road_intel_secret_key_2026"
    GEMINI_API_KEY: str = ""
    JWT_SECRET: str = "tg_road_intel_production_jwt_secret_2026_super_secure"
    JWT_EXPIRE_MINUTES: int = 1440
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI & Research Abuse Protection Limits
    MAX_RESEARCH_SOURCES: int = 10
    MAX_PAGES_PER_SOURCE: int = 5
    MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024  # 10MB
    MAX_GEMINI_CALLS_PER_RESEARCH: int = 5
    RESEARCH_TIMEOUT_SECONDS: int = 60
    MAX_CONCURRENT_RESEARCH_JOBS: int = 3

    # Database Connection Pooling
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30 minutes

    # Redis & Distributed Services
    REDIS_URL: str = ""

    # Logging & Traceability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "JSON"
    CORRELATION_HEADER: str = "X-Request-ID"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_settings(self) -> None:
        """Validates that production environment has all mandatory secrets and safe settings."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG mode must be False in production environment")
            if not self.JWT_SECRET or self.JWT_SECRET == "tg_road_intel_production_jwt_secret_2026_super_secure":
                raise ValueError("Production JWT_SECRET must be explicitly set to a custom strong secret")
            if self.CORS_ORIGINS == "*":
                raise ValueError("Wildcard '*' CORS origins are strictly forbidden in production")

settings = Settings()
try:
    settings.validate_production_settings()
except Exception as e:
    import logging
    logging.getLogger("config").warning(f"Production settings warning: {e}")

