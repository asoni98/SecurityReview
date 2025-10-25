from datetime import timedelta
import secrets
from typing import Optional
from urllib.parse import quote_plus

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PRODUCTION: bool = True
    DEBUG: bool = False

    PROJECT_NAME: str = "yoctogram"
    API_PREFIX: str = "/api/v1"
    FORWARD_FACING_HOSTNAME: str

    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_CONNECTION_STRING: Optional[PostgresDsn] = None

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_CONNECTION_STRING: Optional[RedisDsn] = None

    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"

    IMAGE_PAGINATION: int = 100

    AWS_DEFAULT_REGION: str = "us-west-2"
    S3_ENDPOINT: str = f"https://s3.{AWS_DEFAULT_REGION}.amazonaws.com"
    IMAGES_BUCKET: str
    IMAGES_CLOUDFRONT_DISTRIBUTION: str = None
    PRESIGNED_URL_EXPIRY: int = int(timedelta(days=7).total_seconds())

    @field_validator("POSTGRES_CONNECTION_STRING", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=quote_plus(info.data.get("POSTGRES_PASSWORD")),
            host=info.data.get("POSTGRES_HOST"),
            port=info.data.get("POSTGRES_PORT"),
            path=info.data.get("POSTGRES_DB"),
        )

    @field_validator("REDIS_CONNECTION_STRING", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return RedisDsn.build(
            scheme="redis",
            host=info.data.get("REDIS_HOST"),
            port=info.data.get("REDIS_PORT"),
        )

    @field_validator("IMAGES_CLOUDFRONT_DISTRIBUTION", mode="before")
    @classmethod
    def require_cloudfront_in_prod(cls, v: str, info: ValidationInfo) -> str:
        if not info.data.get("PRODUCTION"):
            return "unused"
        if not isinstance(v, str):
            raise ValueError("Require Cloudfront distribution name in production")
        return v

    class Config:
        case_sensitive = True


settings = Settings()
