from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "DFTPC System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "secretkey123"

    # Database
    DATABASE_URL: str = "postgresql://postgres:12345@localhost:5432/dftpc_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 0

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes

    # External Database
    EXTERNAL_DB_HOST: str = ""
    EXTERNAL_DB_PORT: int = 5432
    EXTERNAL_DB_NAME: str = ""
    EXTERNAL_DB_USER: str = ""
    EXTERNAL_DB_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "jwtsecretkey123"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@sasref.com"

    # Plant Configuration
    PLANT_DESIGN_CAPACITY: float = 10.33  # MT/hr H2 — PAP contract minimum delivery baseline
    PLANT_MAX_CAPACITY: float = 13.5      # MT/hr H2 — sustained operational ceiling (actual observed max)

    # PAP Thresholds — DSQm (Delivery Shortfall Quantity)
    DSQM_REQUIRED_H2_MT_HR: float = 8.5        # MT/hr minimum H2 delivery
    DSQM_PRESSURE_THRESHOLD: float = 22.5       # barg minimum delivery pressure
    DSQM_DURATION_MINUTES: int = 15             # minutes before event triggers
    DSQM_PENALTY_RATE: float = 100.0            # INR per MT shortfall

    # PAP Thresholds — FEPPm (Feedstock Excess Penalty)
    FEPPM_TARGET_FEEDSTOCK_TDAY: float = 715.8  # T/day target feedstock
    FEPPM_DEVIATION_PERCENT: float = 2.5        # % allowed deviation

    # PAP Thresholds — PEPPm (Power Excess Penalty)
    PEPPM_TARGET_MWH_PER_MT: float = 0.53       # MWh per MT H2
    PEPPM_ALLOWABLE_DEVIATION: float = 0.05     # 5% allowed deviation

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
