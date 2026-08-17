from datetime import datetime

from pydantic import Field

from .common import CommonModel


class PasswordResetToken(CommonModel):
    user_id: str = Field(..., alias='userId')
    token_hash: str = Field(..., alias='tokenHash')
    expires_at: datetime = Field(..., alias='expiresAt')
