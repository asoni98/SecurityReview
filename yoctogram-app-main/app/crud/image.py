from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
from pydantic import UUID4

from app.models import Image


async def get_image(
    db: AsyncDBSession,
    image_id: UUID4,
    user_id: UUID4 | None,
) -> Image | None:
    return (
        await db.scalars(
            select(Image).where(
                Image.id == image_id,
                or_(Image.owner_id == user_id if user_id else false(), Image.public),
                Image.uploaded == True,
            )
        )
    ).first()
