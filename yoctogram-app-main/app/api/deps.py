from typing import AsyncGenerator, Generator

from boto3 import Session as AWSSession
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey
from redis.asyncio import Redis, ConnectionPool as RedisConnectionPool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
import structlog

from app.core.config import settings
from app.db.session import session_manager
from app.models import User
from app.schemas.user import UserDetail

logger = structlog.stdlib.get_logger("deps")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
redis_pool = RedisConnectionPool.from_url(
    settings.REDIS_CONNECTION_STRING.unicode_string(),
    encoding="utf-8",
    decode_responses=True,
)


async def get_db() -> AsyncGenerator[AsyncDBSession, None]:
    async with session_manager.session() as session:
        yield session


def get_aws_session() -> Generator[AWSSession, None, None]:
    session = AWSSession()
    yield session


def get_redis() -> Generator[Redis, None, None]:
    redis = Redis(connection_pool=redis_pool)
    yield redis


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncDBSession = Depends(get_db)
) -> UserDetail:
    try:
        key = OctKey.import_key(settings.JWT_SECRET_KEY)
        claims_requests = jwt.JWTClaimsRegistry()

        claims = jwt.decode(token, key).claims
        claims_requests.validate(claims)

        uid: str = claims.get("sub")
        if uid is None:
            raise HTTPException(status_code=400, detail="Invalid token")

        db_user = (await db.scalars(select(User).where(User.id == uid))).first()
        if db_user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return UserDetail(id=uid, username=db_user.username, email=db_user.email)
    except JoseError as e:
        await logger.ainfo("Exception decoding JWT")
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def verify_jwt_to_uuid_or_none(
    token: str = Depends(oauth2_scheme), db: AsyncDBSession = Depends(get_db)
) -> UserDetail | None:
    try:
        user = await get_current_user(token, db)
        return user
    except HTTPException:
        await logger.ainfo(
            "No user found (likely no JWT provided), continuing without auth"
        )
        return None
