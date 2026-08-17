from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from urllib.parse import urlencode

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from roleplay_catalogue.services import DatabaseService, MailingService

from roleplay_catalogue.misc import (
    InvalidActivationToken,
    InvalidPasswordResetToken,
    UserAlreadyExists,
    UserCredentialMismatch,
    UserNotFound,
    UserRole,
    UserStatus,
)
from roleplay_catalogue.models import ActivationToken, ApiKey, PasswordResetToken, User


class AuthComponent:
    def __init__(self,
                 database: DatabaseService,
                 mailing: MailingService,
                 public_base_url: str,
                 activation_token_max_age: int,
                 password_reset_token_max_age: int = 3600,
                 ):
        self._db = database
        self._mailing = mailing
        self._public_base_url = public_base_url.rstrip('/')
        self._activation_token_max_age = activation_token_max_age
        self._password_reset_token_max_age = password_reset_token_max_age
        self._hasher = PasswordHasher()

    async def create_api_key(self, user: User, name: str,
                             lifetime: timedelta | None) -> tuple[ApiKey, str]:
        secret = token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + lifetime if lifetime else None
        api_key = ApiKey(
            userId=user.id,
            name=name.strip(),
            keyHash=sha256(secret.encode()).hexdigest(),
            expiresAt=expires_at,
        )
        return await self._db.api_key.create(api_key), secret

    async def authenticate_api_key(self, credential: str) -> User:
        try:
            key_id, secret = credential.split(':', 1)
        except ValueError as error:
            raise UserCredentialMismatch('Invalid API key') from error
        api_key = await self._db.api_key.get(key_id)
        now = datetime.now(timezone.utc)
        if not api_key:
            raise UserCredentialMismatch('Invalid API key')
        if api_key.expires_at is not None and api_key.expires_at <= now:
            await self._db.api_key.delete(api_key.id)
            raise UserCredentialMismatch('API key has expired')
        supplied_hash = sha256(secret.encode()).hexdigest()
        if not compare_digest(api_key.key_hash, supplied_hash):
            raise UserCredentialMismatch('Invalid API key')
        user = await self._db.user.get(api_key.user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise UserCredentialMismatch('Invalid API key')
        return user

    async def purge_expired_api_keys(self) -> int:
        return await self._db.api_key.delete_expired(datetime.now(timezone.utc))

    async def list_api_keys(self, user: User) -> list[ApiKey]:
        return await self._db.api_key.list_for_user(user.id)

    async def revoke_api_key(self, user: User, key_id: str) -> bool:
        return await self._db.api_key.delete(key_id, user.id)

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

    def verify_password(self, user: User, password: str) -> None:
        try:
            self._hasher.verify(user.password_hash, password)
        except VerificationError as error:
            raise UserCredentialMismatch('Current password is incorrect') from error

    async def change_password(self, user: User, current_password: str,
                              new_password: str) -> User:
        self.verify_password(user, current_password)
        updated = user.model_copy(update={'password_hash': self._hasher.hash(new_password)})
        await self._db.password_reset_token.delete(user.id)
        return await self._db.user.update(updated)

    async def request_password_reset(self, email: str) -> None:
        user = await self._db.user.get_by_email(email.strip().casefold())
        if not user or user.status != UserStatus.ACTIVE:
            return
        raw_token = token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._password_reset_token_max_age,
        )
        await self._db.password_reset_token.create(PasswordResetToken(
            userId=user.id,
            tokenHash=self._hasher.hash(raw_token),
            expiresAt=expires_at,
        ))
        query = urlencode({'userId': user.id, 'token': raw_token})
        reset_url = f'{self._public_base_url}/reset-password?{query}'
        expires_in_minutes = max(1, self._password_reset_token_max_age // 60)
        html_body = self._mailing.render_template(
            'password_reset.html', username=user.username, reset_url=reset_url,
            expires_in_minutes=expires_in_minutes,
        )
        try:
            await self._mailing.send_email(
                recipients=user.email,
                subject='Reset your Roleplay Catalogue password',
                text_body=(
                    f'Hello {user.username},\n\nReset your password by visiting: {reset_url}\n\n'
                    f'This link expires in {expires_in_minutes} minutes.'
                ),
                html_body=html_body,
            )
        except Exception:
            await self._db.password_reset_token.delete(user.id)
            raise

    async def reset_password(self, user_id: str, token: str, new_password: str) -> User:
        user = await self._db.user.get(user_id)
        reset_token = await self._db.password_reset_token.get(user_id)
        if not user or not reset_token or user.status != UserStatus.ACTIVE:
            raise InvalidPasswordResetToken()
        if reset_token.expires_at <= datetime.now(timezone.utc):
            await self._db.password_reset_token.delete(user_id)
            raise InvalidPasswordResetToken()
        try:
            self._hasher.verify(reset_token.token_hash, token)
        except VerificationError as error:
            raise InvalidPasswordResetToken() from error
        updated = user.model_copy(update={'password_hash': self._hasher.hash(new_password)})
        await self._db.user.update(updated)
        await self._db.password_reset_token.delete(user_id)
        return updated

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
