from pydantic import BaseModel, UUID4


class CommentCreate(BaseModel):
    content: str
