from typing import Any, Dict, List

from boto3.session import Session as AWSSession
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession

from app.core.config import settings
from app.ext.s3 import presigned_url_with_cache
from app.models import Image


async def build_feed(
    filters: List[Any],
    db: AsyncDBSession,
    aws: AWSSession,
    redis: Redis,
) -> Dict[str, str | int]:
    filters.append(Image.uploaded == True)
    db_images = await db.stream_scalars(
        select(Image)
        .where(*filters)
        .order_by(Image.created_at.desc())
        .limit(settings.IMAGE_PAGINATION)
    )

    return_content = {"success": True, "count": 0, "results": []}
    async for image_record in db_images:
        return_content["results"].append(
            {
                "id": str(image_record.id),
                "creator": str(image_record.owner_id),
                "download_url": await presigned_url_with_cache(
                    aws,
                    redis,
                    image_record.path,
                    image_record.content_type,
                ),
                "created_at": image_record.created_at.timestamp(),
                "caption": image_record.caption,
                "like_count": len(await image_record.awaitable_attrs.likes),
            }
        )
        return_content["count"] += 1

    return return_content
