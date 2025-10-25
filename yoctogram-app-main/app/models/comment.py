from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ulid import ULID

from app.db.base_class import Base


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=ULID().to_uuid4())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="comments")
    image_id: Mapped[UUID] = mapped_column(ForeignKey("image.id"))
    image: Mapped["Image"] = relationship(back_populates="comments")
    content: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
