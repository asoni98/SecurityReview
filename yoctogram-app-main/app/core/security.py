from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt

from joserfc import jwt
from joserfc.jwk import OctKey

from app.core.config import settings


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    key = OctKey.import_key(settings.JWT_SECRET_KEY)
    header = {"alg": settings.JWT_ALGORITHM}
    claims = {"exp": expire, "sub": str(subject)}

    return jwt.encode(header, claims, key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
