from datetime import datetime, timezone
from uuid import UUID
from typing import List

from sqlalchemy.orm import relationship, Mapped, mapped_column
from ulid import ULID

from app.db.base_class import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, index=True, default=ULID().to_uuid4()
    )
    username: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    bio: Mapped[str] = mapped_column(nullable=True)
    images: Mapped[List["Image"]] = relationship(back_populates="owner")
    likes: Mapped[List["Like"]] = relationship(back_populates="user")
    comments: Mapped[List["Comment"]] = relationship(back_populates="user")
