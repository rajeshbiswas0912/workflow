from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator, model_validator
from sqlalchemy.engine import URL
from app.config.aws_secrets import load_aws_secrets

load_aws_secrets()

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- App ----
    APP_NAME: str = "Todo API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    # ---- Database ----
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    DB_POOL_SIZE: int = Field(default=10, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=1)
    DB_ECHO: bool = False

    # ---- Security ----
    SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, gt=0)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=16)

    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    ADMIN_ROLE_ID: int

    LOW_STOCK_THRESHOLD: int

    EMAIL_QUEUE_URL: str = ""
    EMAIL_FROM: str = ""
    APP_LOGIN_URL: str = ""
    AWS_REGION_NAME: str = "ap-southeast-2"

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _no_debug_in_production(self) -> "Settings":
        if self.APP_ENV == "production" and self.DEBUG:
            raise ValueError("DEBUG must be false when APP_ENV=production")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"sslmode": "require"} if self.is_production else {},
        )

@lru_cache
def get_settings() -> Settings:
    return Settings() # type: ignore[call-arg]

settings = get_settings()
