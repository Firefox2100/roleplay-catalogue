from uuid import uuid4
from pydantic import Field

from roleplay_catalogue.misc import UserRole
from .common import CommonModel


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
