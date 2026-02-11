from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    PGHOST: str = "localhost"
    PGPORT: int = 5432
    PGUSER: str = "scan"
    PGPASSWORD: str
    PGDATABASE: str = "scanner"

    # Redis — configured in docker-compose.yml (used by Celery broker/backend)
    # but NOT used by the FastAPI app_api yet. The app uses in-memory TTL caches
    # for dashboard stats and presigned URLs. Consider migrating to Redis for
    # shared/distributed caching when scaling beyond a single API process.
    REDIS_URL: str = "redis://redis:6379/0"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:80"
    LOG_LEVEL: str = "INFO"

    # Cache TTLs (seconds)
    CACHE_DASHBOARD_TTL: int = 30
    CACHE_GEOGRAPHY_TTL: int = 3600
    CACHE_PLAYLISTS_TTL: int = 300

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "scanner"
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str = "feeds"
    MINIO_USE_SSL: bool = False

    # Firebase Admin SDK
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "/opt/policescanner/secrets/firebase-service-account.json"

    # Session cookies
    SESSION_COOKIE_NAME: str = "scanner_session"
    SESSION_COOKIE_SECURE: bool = False     # Set to True for HTTPS in production
    SESSION_COOKIE_HTTPONLY: bool = True    # Not accessible via JavaScript
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_MAX_AGE: int = 604800    # 7 days in seconds

    # Admin seeding - first login with this email becomes admin
    ADMIN_EMAIL: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
