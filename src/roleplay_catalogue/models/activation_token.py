from datetime import datetime

from pydantic import Field

from .common import CommonModel


class ActivationToken(CommonModel):
    username: str = Field(
        ...,
        description='Username associated with the activation request',
    )
    token_hash: str = Field(
        ...,
        description='Argon2 hash of the activation token',
        alias='tokenHash',
    )
    expires_at: datetime = Field(
        ...,
        description='Time after which the token must not be accepted',
        alias='expiresAt',
    )
