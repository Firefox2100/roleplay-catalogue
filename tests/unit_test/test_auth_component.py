from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from argon2 import PasswordHasher

from roleplay_catalogue.components import AuthComponent
from roleplay_catalogue.misc import (
    InvalidActivationToken,
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


class MemoryDatabaseService:
    def __init__(self):
        self.user = MemoryUserRepository()
        self.activation_token = MemoryActivationTokenRepository()


class MemoryMailingService:
    def __init__(self):
        self.messages = []

    def render_template(self, template_name, **context):
        return f'{template_name}: {context["activation_url"]}'

    async def send_email(self, **message):
        self.messages.append(message)


def create_auth_component():
    database = MemoryDatabaseService()
    mailing = MemoryMailingService()
    auth = AuthComponent(
        database=database,
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
