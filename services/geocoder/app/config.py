
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    PGHOST: str = "postgres"
    PGPORT: int = 5432
    PGUSER: str = "scan"
    PGPASSWORD: str = ""
    PGDATABASE: str = "scanner"

    # Nominatim API
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"
    NOMINATIM_USER_AGENT: str = "police-scanner-app"
    GEOCODE_RATE_LIMIT: float = 1.0  # requests per second

    # Service
    LOG_LEVEL: str = "INFO"
    BATCH_SIZE: int = 100  # locations to process per batch
    MAX_GEOCODE_ATTEMPTS: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"


settings = Settings()
