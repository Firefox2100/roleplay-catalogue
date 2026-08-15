from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from roleplay_catalogue.services import DatabaseService

from roleplay_catalogue.misc import UserNotFound, UserCredentialMismatch
from roleplay_catalogue.models import User


class AuthComponent:
    def __init__(self,
                 database: DatabaseService,
                 ):
        self._db = database
        self._hasher = PasswordHasher()

    async def authenticate_user(self,
                                username: str,
                                password: str,
                                ) -> User:
        user = await self._db.user.get_by_username(username)

        if not user:
            raise UserNotFound(f'User with username {username} not found')

        try:
            self._hasher.verify(
                hash=user.password_hash,
                password=password,
            )
        except VerifyMismatchError:
            raise UserCredentialMismatch(f'User {user.id} provided wrong password')

        return user
