from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ulid import ULID

from app.db.base_class import Base


class Image(Base):
    __tablename__ = "image"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=ULID().to_uuid4())
    path: Mapped[str] = mapped_column()
    content_type: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    public: Mapped[bool] = mapped_column(default=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    owner: Mapped["User"] = relationship(back_populates="images")
    uploaded: Mapped[bool] = mapped_column(default=False)
    caption: Mapped[str] = mapped_column()
    likes: Mapped[List["Like"]] = relationship(back_populates="image")
    comments: Mapped[List["Comment"]] = relationship(back_populates="image")
