from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from argon2 import PasswordHasher

from roleplay_catalogue.components import AuthComponent
from roleplay_catalogue.misc import (
    InvalidActivationToken,
    InvalidPasswordResetToken,
    UserAlreadyExists,
    UserCredentialMismatch,
    UserRole,
    UserStatus,
)


class MemoryUserRepository:
    def __init__(self):
        self.users = {}

    async def get_by_username(self, username):
        return next((user for user in self.users.values() if user.username == username), None)

    async def get(self, user_id):
        return self.users.get(user_id)

    async def get_by_email(self, email):
        return next((user for user in self.users.values() if user.email == email), None)

    async def create(self, user):
        self.users[user.id] = user
        return user

    async def has_any(self):
        return bool(self.users)

    async def update(self, user):
        self.users[user.id] = user
        return user


class MemoryActivationTokenRepository:
    def __init__(self):
        self.tokens = {}

    async def create(self, token):
        self.tokens[token.username] = token
        return token

    async def get(self, username):
        return self.tokens.get(username)

    async def delete(self, username):
        return self.tokens.pop(username, None) is not None


class MemoryPasswordResetTokenRepository:
    def __init__(self):
        self.tokens = {}

    async def create(self, token):
        self.tokens[token.user_id] = token
        return token

    async def get(self, user_id):
        return self.tokens.get(user_id)

    async def delete(self, user_id):
        return self.tokens.pop(user_id, None) is not None


class MemoryApiKeyRepository:
    def __init__(self):
        self.keys = {}

    async def create(self, api_key):
        self.keys[api_key.id] = api_key
        return api_key

    async def get(self, key_id):
        return self.keys.get(key_id)

    async def list_for_user(self, user_id):
        return [key for key in self.keys.values() if key.user_id == user_id]

    async def delete(self, key_id, user_id=None):
        key = self.keys.get(key_id)
        if not key or (user_id is not None and key.user_id != user_id):
            return False
        del self.keys[key_id]
        return True

    async def delete_expired(self, now):
        expired = [key_id for key_id, key in self.keys.items()
                   if key.expires_at is not None and key.expires_at <= now]
        for key_id in expired:
            del self.keys[key_id]
        return len(expired)


class MemoryDatabaseService:
    def __init__(self):
        self.user = MemoryUserRepository()
        self.activation_token = MemoryActivationTokenRepository()
        self.password_reset_token = MemoryPasswordResetTokenRepository()
        self.api_key = MemoryApiKeyRepository()


class MemoryMailingService:
    def __init__(self):
        self.messages = []

    def render_template(self, template_name, **context):
        return f'{template_name}: {context.get("activation_url") or context.get("reset_url")}'

    async def send_email(self, **message):
        self.messages.append(message)


def create_auth_component():
    database = MemoryDatabaseService()
    mailing = MemoryMailingService()
    auth = AuthComponent(
        database=database,
        cache=database,
        mailing=mailing,
        public_base_url='https://catalogue.example',
        activation_token_max_age=3600,
    )
    return auth, database, mailing


async def test_registration_stores_hashes_and_sends_activation_email() -> None:
    auth, database, mailing = create_auth_component()

    user = await auth.register_user('alice', 'Alice@Example.com', 'correct-password')

    assert user.status == UserStatus.PENDING_ACTIVATION
    assert user.role == UserRole.ADMIN
    assert user.email == 'alice@example.com'
    assert user.password_hash != 'correct-password'
    PasswordHasher().verify(user.password_hash, 'correct-password')

    message = mailing.messages[0]
    activation_url = message['text_body'].split('visiting: ', 1)[1].splitlines()[0]
    assert urlsplit(activation_url).path == '/api/auth/activation'
    query = parse_qs(urlsplit(activation_url).query)
    raw_token = query['token'][0]
    stored_token = database.activation_token.tokens[user.username]
    assert stored_token.token_hash != raw_token
    PasswordHasher().verify(stored_token.token_hash, raw_token)


async def test_pending_user_cannot_login_and_valid_token_activates() -> None:
    auth, database, mailing = create_auth_component()
    user = await auth.register_user('alice', 'alice@example.com', 'correct-password')

    with pytest.raises(UserCredentialMismatch):
        await auth.authenticate_user('alice', 'correct-password')

    activation_url = mailing.messages[0]['text_body'].split('visiting: ', 1)[1].splitlines()[0]
    token = parse_qs(urlsplit(activation_url).query)['token'][0]
    active_user = await auth.activate_user('alice', token)

    assert active_user.status == UserStatus.ACTIVE
    assert 'alice' not in database.activation_token.tokens
    assert await auth.authenticate_user('alice', 'correct-password') == active_user
    assert database.user.users[user.id].status == UserStatus.ACTIVE


async def test_invalid_activation_token_is_rejected() -> None:
    auth, _, _ = create_auth_component()
    await auth.register_user('alice', 'alice@example.com', 'correct-password')

    with pytest.raises(InvalidActivationToken):
        await auth.activate_user('alice', 'invalid-token')


async def test_expired_activation_token_is_deleted_and_rejected() -> None:
    auth, database, mailing = create_auth_component()
    await auth.register_user('alice', 'alice@example.com', 'correct-password')
    stored_token = database.activation_token.tokens['alice']
    database.activation_token.tokens['alice'] = stored_token.model_copy(update={
        'expires_at': datetime.now(timezone.utc) - timedelta(seconds=1),
    })
    activation_url = mailing.messages[0]['text_body'].split('visiting: ', 1)[1].splitlines()[0]
    token = parse_qs(urlsplit(activation_url).query)['token'][0]

    with pytest.raises(InvalidActivationToken):
        await auth.activate_user('alice', token)
    assert 'alice' not in database.activation_token.tokens


async def test_registration_checks_username_and_email_uniqueness() -> None:
    auth, _, _ = create_auth_component()
    await auth.register_user('alice', 'alice@example.com', 'correct-password')

    with pytest.raises(UserAlreadyExists):
        await auth.register_user('alice', 'other@example.com', 'correct-password')
    with pytest.raises(UserAlreadyExists):
        await auth.register_user('other', 'ALICE@example.com', 'correct-password')


async def test_only_first_registered_user_is_admin() -> None:
    auth, _, _ = create_auth_component()

    first = await auth.register_user('alice', 'alice@example.com', 'correct-password')
    second = await auth.register_user('bob', 'bob@example.com', 'correct-password')

    assert first.role == UserRole.ADMIN
    assert second.role == UserRole.USER


async def test_password_reset_token_is_hashed_one_time_and_changes_password() -> None:
    auth, database, mailing = create_auth_component()
    user = await auth.register_user('alice', 'alice@example.com', 'old-password')
    database.user.users[user.id] = user.model_copy(update={'status': UserStatus.ACTIVE})

    await auth.request_password_reset('ALICE@example.com')

    reset_url = mailing.messages[-1]['text_body'].split('visiting: ', 1)[1].splitlines()[0]
    raw_token = parse_qs(urlsplit(reset_url).query)['token'][0]
    stored = database.password_reset_token.tokens[user.id]
    assert stored.token_hash != raw_token

    await auth.reset_password(user.id, raw_token, 'new-password')
    assert user.id not in database.password_reset_token.tokens
    assert await auth.authenticate_user('alice', 'new-password')
    with pytest.raises(InvalidPasswordResetToken):
        await auth.reset_password(user.id, raw_token, 'another-password')


async def test_change_password_requires_current_password() -> None:
    auth, database, _ = create_auth_component()
    user = await auth.register_user('alice', 'alice@example.com', 'old-password')
    user = user.model_copy(update={'status': UserStatus.ACTIVE})
    database.user.users[user.id] = user

    with pytest.raises(UserCredentialMismatch):
        await auth.change_password(user, 'wrong-password', 'new-password')
    await auth.change_password(user, 'old-password', 'new-password')
    assert await auth.authenticate_user('alice', 'new-password')


async def test_api_key_is_stored_hashed_authenticates_and_revokes() -> None:
    auth, database, _ = create_auth_component()
    user = await auth.register_user('alice', 'alice@example.com', 'old-password')
    user = user.model_copy(update={'status': UserStatus.ACTIVE})
    database.user.users[user.id] = user

    api_key, secret = await auth.create_api_key(user, 'External client', timedelta(days=7))

    assert secret not in api_key.key_hash
    assert await auth.authenticate_api_key(f'{api_key.id}:{secret}') == user
    with pytest.raises(UserCredentialMismatch):
        await auth.authenticate_api_key(f'{api_key.id}:wrong')

    assert await auth.revoke_api_key(user, api_key.id)
    with pytest.raises(UserCredentialMismatch):
        await auth.authenticate_api_key(f'{api_key.id}:{secret}')
