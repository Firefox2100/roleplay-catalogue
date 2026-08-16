from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import urlencode

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from roleplay_catalogue.services import DatabaseService, MailingService

from roleplay_catalogue.misc import (
    InvalidActivationToken,
    UserAlreadyExists,
    UserCredentialMismatch,
    UserNotFound,
    UserRole,
    UserStatus,
)
from roleplay_catalogue.models import ActivationToken, User


class AuthComponent:
    def __init__(self,
                 database: DatabaseService,
                 mailing: MailingService,
                 public_base_url: str,
                 activation_token_max_age: int,
                 ):
        self._db = database
        self._mailing = mailing
        self._public_base_url = public_base_url.rstrip('/')
        self._activation_token_max_age = activation_token_max_age
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
        except VerifyMismatchError as error:
            raise UserCredentialMismatch(
                f'User {user.id} provided wrong password',
            ) from error

        if user.status != UserStatus.ACTIVE:
            raise UserCredentialMismatch(f'User {user.id} is not active')

        return user

    async def register_user(self,
                            username: str,
                            email: str,
                            password: str,
                            ) -> User:
        username = username.strip()
        email = email.strip().casefold()
        if await self._db.user.get_by_username(username):
            raise UserAlreadyExists('Username is already registered')
        if await self._db.user.get_by_email(email):
            raise UserAlreadyExists('Email address is already registered')

        user = User(
            username=username,
            email=email,
            passwordHash=self._hasher.hash(password),
            role=UserRole.USER if await self._db.user.has_any() else UserRole.ADMIN,
            status=UserStatus.PENDING_ACTIVATION,
        )
        raw_token = token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._activation_token_max_age,
        )
        activation_token = ActivationToken(
            username=user.username,
            tokenHash=self._hasher.hash(raw_token),
            expiresAt=expires_at,
        )

        query = urlencode({'username': user.username, 'token': raw_token})
        activation_url = f'{self._public_base_url}/api/auth/activation?{query}'
        expires_in_hours = max(1, self._activation_token_max_age // 3600)
        html_body = self._mailing.render_template(
            'activation.html',
            username=user.username,
            activation_url=activation_url,
            expires_in_hours=expires_in_hours,
        )
        await self._db.activation_token.create(activation_token)
        try:
            await self._mailing.send_email(
                recipients=user.email,
                subject='Activate your Roleplay Catalogue account',
                text_body=(
                    f'Hello {user.username},\n\n'
                    f'Activate your account by visiting: {activation_url}\n\n'
                    f'This link expires in {expires_in_hours} hours.'
                ),
                html_body=html_body,
            )
            await self._db.user.create(user)
        except Exception:
            await self._db.activation_token.delete(user.username)
            raise
        return user

    async def activate_user(self,
                            username: str,
                            token: str,
                            ) -> User:
        user = await self._db.user.get_by_username(username)
        activation_token = await self._db.activation_token.get(username)
        if not user or not activation_token or user.status != UserStatus.PENDING_ACTIVATION:
            raise InvalidActivationToken()
        if activation_token.expires_at <= datetime.now(timezone.utc):
            await self._db.activation_token.delete(username)
            raise InvalidActivationToken()

        try:
            self._hasher.verify(activation_token.token_hash, token)
        except VerificationError as error:
            raise InvalidActivationToken() from error

        active_user = user.model_copy(update={'status': UserStatus.ACTIVE})
        await self._db.user.update(active_user)
        await self._db.activation_token.delete(username)
        return active_user
