from datetime import datetime, timezone
from uuid import uuid4
from pydantic import Field

from roleplay_catalogue.misc import UserRole, UserStatus
from .common import CommonModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(CommonModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='User ID',
    )
    username: str = Field(
        ...,
        description='Username',
    )
    email: str = Field(
        ...,
        description='User email address',
    )
    password_hash: str = Field(
        ...,
        description='User password hash, using Argon2',
        alias='passwordHash',
    )
    role: UserRole = Field(
        UserRole.USER,
        description='User role',
    )
    status: UserStatus = Field(
        UserStatus.ACTIVE,
        description='Account activation and access status',
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description='Time at which the account was created',
        alias='createdAt',
    )
