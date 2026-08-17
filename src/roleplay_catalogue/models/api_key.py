from datetime import datetime
from uuid import uuid4

from pydantic import Field

from .common import CommonModel
from .user import utc_now


class ApiKey(CommonModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str = Field(..., alias='userId')
    name: str = Field(..., min_length=1, max_length=100)
    key_hash: str = Field(..., alias='keyHash')
    created_at: datetime = Field(default_factory=utc_now, alias='createdAt')
    expires_at: datetime | None = Field(None, alias='expiresAt')
