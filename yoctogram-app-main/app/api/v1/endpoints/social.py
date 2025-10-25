from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as AsyncDBSession
from ulid import ULID

from app.api import deps
from app.crud.image import get_image
from app.models import Comment, Like
from app.schemas.comment import CommentCreate
from app.schemas.user import UserDetail

router = APIRouter()


@router.post("/{image_id}/like")
async def images_like(
    image_id: UUID4,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    if (
        await db.scalars(
            select(Like).where(Like.user_id == user.id, Like.image_id == image_id)
        )
    ).first():
        return JSONResponse(
            {"success": False, "detail": "User has already liked this image"},
            status_code=400,
        )

    (await db_image.awaitable_attrs.likes).append(
        Like(user_id=user.id, image_id=image_id, image=db_image)
    )
    await db.commit()
    await db.refresh(db_image)

    return JSONResponse({"success": True})


@router.post("/{image_id}/unlike")
async def images_unlike(
    image_id: UUID4,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    for like in await db_image.awaitable_attrs.likes:
        if like.user_id == user.id:
            await db.delete(like)
            await db.commit()
            await db.refresh(db_image)
            break
    else:
        return JSONResponse(
            {"success": False, "detail": "User has not liked this image"},
            status_code=400,
        )

    return JSONResponse({"success": True})


@router.get("/{image_id}/likes")
async def images_get_likes(
    image_id: UUID4,
    user: UserDetail | None = Depends(deps.verify_jwt_to_uuid_or_none),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    liking_users = [
        {
            "id": str(like.user_id),
            "username": (await like.awaitable_attrs.user).username,
        }
        for like in await db_image.awaitable_attrs.likes
    ]

    return JSONResponse({"success": True, "likes": liking_users})


@router.post("/{image_id}/comment")
async def images_comment(
    image_id: UUID4,
    comment: CommentCreate,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    (await db_image.awaitable_attrs.comments).append(
        Comment(
            id=ULID().to_uuid4(),
            user_id=user.id,
            image_id=image_id,
            content=comment.content,
        )
    )
    await db.commit()
    await db.refresh(db_image)

    return JSONResponse({"success": True})


@router.post("/{image_id}/comments/{comment_id}/update")
async def images_comment(
    image_id: UUID4,
    comment_id: UUID4,
    comment: CommentCreate,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    for db_comment in await db_image.awaitable_attrs.comments:
        if db_comment.id == comment_id:
            db_comment.content = comment.content
            await db.commit()
            await db.refresh(db_image)
            break
    else:
        return JSONResponse(
            {"success": False, "detail": "Comment not found"}, status_code=404
        )

    return JSONResponse({"success": True})


@router.post("/{image_id}/comments/{comment_id}/delete")
async def images_comment(
    image_id: UUID4,
    comment_id: UUID4,
    user: UserDetail = Depends(deps.get_current_user),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    for comment in await db_image.awaitable_attrs.comments:
        if comment.id == comment_id:
            await db.delete(comment)
            await db.commit()
            await db.refresh(db_image)
            break
    else:
        return JSONResponse(
            {"success": False, "detail": "Comment not found"}, status_code=404
        )

    return JSONResponse({"success": True})


@router.get("/{image_id}/comments")
async def images_get_comments(
    image_id: UUID4,
    user: UserDetail | None = Depends(deps.verify_jwt_to_uuid_or_none),
    db: AsyncDBSession = Depends(deps.get_db),
) -> Response:
    db_image = await get_image(db, image_id, user.id)
    if not db_image:
        return JSONResponse(
            {"success": False, "detail": "Image not found"}, status_code=404
        )

    comments = [
        {
            "id": str(comment.id),
            "user_id": str(comment.user_id),
            "username": (await comment.awaitable_attrs.user).username,
            "content": comment.content,
            "created_at": comment.created_at.timestamp(),
        }
        for comment in await db_image.awaitable_attrs.comments
    ]

    return JSONResponse({"success": True, "comments": comments})
