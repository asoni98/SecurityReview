from boto3.session import Session as AWSSession
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import UUID4
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
import structlog
from ulid import ULID

from app.api import deps
from app.ext.s3 import create_presigned_post, presigned_url_with_cache, verify_exists
from app.core.config import settings
from app.crud.image import get_image
from app.models import Image
from app.schemas.user import UserDetail

router = APIRouter()
logger = structlog.stdlib.get_logger("api.images")


@router.post("/upload/{privacy}/generate")
async def images_generate_upload_link(
    privacy: str,
    caption: str = "",
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
    aws: AWSSession = Depends(deps.get_aws_session),
) -> Response:
    if privacy not in ["public", "private"]:
        return JSONResponse(
            content={
                "success": False,
                "detail": "privacy parameter should be 'public' or 'private'",
            },
            status_code=400,
        )

    public = privacy == "public"
    image_id = str(ULID().to_uuid4())
    db_image = Image(
        id=image_id,
        public=public,
        caption=caption,
        owner_id=user.id,
        content_type="image/jpeg",
    )

    presigned_post = create_presigned_post(aws, image_id)
    db_image.path = presigned_post["s3_uri"]
    create_response = presigned_post["create_response"] | {"id": image_id}

    db.add(db_image)
    await db.commit()
    await db.refresh(db_image)

    return JSONResponse({"success": True} | create_response)


@router.post("/upload/{image_id}/confirm")
async def images_confirm_uploaded(
    image_id: UUID4,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
    aws: AWSSession = Depends(deps.get_aws_session),
) -> Response:
    db_image = (await db.scalars(select(Image).where(Image.id == image_id))).first()
    if (not db_image) or (db_image.owner_id != user.id):
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    if db_image.uploaded:
        return JSONResponse(
            {"success": False, "detail": "Image upload already confirmed"},
            status_code=404,
        )

    if not verify_exists(aws, db_image.path):
        return JSONResponse(
            {"success": False, "detail": "Image with that ID doesn't exist in S3"},
            status_code=404,
        )

    db_image.uploaded = True
    db.add(db_image)
    await db.commit()
    await db.refresh(db_image)

    return JSONResponse({"success": True})


# Image retrieval route
@router.get("/media/{image_id}")
async def images_retrieve(
    image_id: UUID4,
    user: UserDetail | None = Depends(deps.verify_jwt_to_uuid_or_none),
    db: AsyncDBSession = Depends(deps.get_db),
    aws: AWSSession = Depends(deps.get_aws_session),
    redis: Redis = Depends(deps.get_redis),
) -> Response:
    try:
        user_id = user.id if user is not None else None
        db_image = await get_image(db, image_id, user_id)
        if not db_image:
            return JSONResponse(
                {"success": False, "detail": "Image not found"}, status_code=404
            )

        return JSONResponse(
            {
                "success": True,
                "uri": await presigned_url_with_cache(
                    aws, redis, db_image.path, db_image.content_type
                ),
            }
        )

    except Exception as e:
        await logger.aexception("Error retrieving image", image=image_id, user=user_id)
        return JSONResponse(
            {
                "success": False,
                "detail": str(e) if settings.DEBUG else "Internal server error",
            },
            status_code=500,
        )
