from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ulid import ULID

from app.db.base_class import Base


class Like(Base):
    __tablename__ = "like"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=ULID().to_uuid4())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    user: Mapped["User"] = relationship(back_populates="likes")
    image_id: Mapped[UUID] = mapped_column(ForeignKey("image.id"))
    image: Mapped["Image"] = relationship(back_populates="likes")
