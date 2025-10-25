from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from boto3.session import Session as AWSSession
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
import structlog

from app.api import deps
from app.core.config import settings
from app.crud.feed import build_feed
from app.models import Image
from app.schemas.user import UserDetail

router = APIRouter()
logger = structlog.stdlib.get_logger("api.feed")


@router.get("/latest")
async def feed_latest(
    before: datetime = datetime.now(tz=timezone.utc) + timedelta(days=1),  # buffer for timezones
    after: datetime = datetime.fromtimestamp(0, tz=timezone.utc),
    user: UserDetail | None = Depends(deps.verify_jwt_to_uuid_or_none),
    db: AsyncDBSession = Depends(deps.get_db),
    aws: AWSSession = Depends(deps.get_aws_session),
    redis: Redis = Depends(deps.get_redis),
) -> Response:
    try:
        before = before.astimezone(timezone.utc).replace(tzinfo=None)
        after = after.astimezone(timezone.utc).replace(tzinfo=None)

        image_filters = [
            Image.created_at < before,
            Image.created_at > after,
            Image.public,
        ]

        if user is not None:
            image_filters[-1] = or_(Image.public, Image.owner_id == user.id)

        return JSONResponse(await build_feed(image_filters, db, aws, redis))
    except Exception as e:
        await logger.aexception("Error building latest feed", user=user.id)
        return JSONResponse(
            {
                "success": False,
                "detail": str(e) if settings.DEBUG else "Internal server error",
            },
            status_code=500,
        )


@router.get("/by_user/{creator}")
async def feed_by_user(
    creator: uuid.UUID,
    before: datetime = datetime.now(tz=timezone.utc) + timedelta(days=1),  # buffer for timezones
    after: datetime = datetime.fromtimestamp(0, tz=timezone.utc),
    user: UserDetail | None = Depends(deps.verify_jwt_to_uuid_or_none),
    db: AsyncDBSession = Depends(deps.get_db),
    aws: Optional[AWSSession] = Depends(deps.get_aws_session),
    redis: Redis = Depends(deps.get_redis),
) -> Response:
    try:
        before = before.astimezone(timezone.utc).replace(tzinfo=None)
        after = after.astimezone(timezone.utc).replace(tzinfo=None)

        image_filters = [
            Image.created_at < before,
            Image.created_at > after,
            Image.owner_id == creator,
            or_(Image.owner_id == user.id, Image.public),
        ]

        return JSONResponse(await build_feed(image_filters, db, aws, redis))
    except Exception as e:
        await logger.aexception(
            "Error building by_user feed", user=user.id, creator=creator
        )
        return JSONResponse(
            {
                "success": False,
                "detail": str(e) if settings.DEBUG else "Internal server error",
            },
            status_code=500,
        )
