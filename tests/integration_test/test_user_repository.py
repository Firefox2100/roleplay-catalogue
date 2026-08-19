from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import DuplicateKeyError

from roleplay_catalogue.misc import UserStatus
from roleplay_catalogue.models import User


def make_user(**overrides) -> User:
    # Mongo dates are millisecond-precision; round createdAt so equality checks pass.
    defaults = {
        'username': 'alice', 'email': 'alice@example.com', 'passwordHash': 'hash',
        'createdAt': datetime.now(timezone.utc).replace(microsecond=0),
    }
    return User(**{**defaults, **overrides})


async def test_create_get_update_and_delete_round_trip(database_service) -> None:
    user = await database_service.user.create(make_user())

    assert await database_service.user.get(user.id) == user
    assert await database_service.user.get_by_username('alice') == user
    assert await database_service.user.get_by_email('alice@example.com') == user
    assert await database_service.user.get('missing') is None

    updated = user.model_copy(update={'status': UserStatus.ACTIVE})
    await database_service.user.update(updated)
    assert (await database_service.user.get(user.id)).status == UserStatus.ACTIVE

    assert await database_service.user.delete(user.id) is True
    assert await database_service.user.get(user.id) is None
    assert await database_service.user.delete(user.id) is False


async def test_has_any_reflects_whether_a_user_exists(database_service) -> None:
    assert await database_service.user.has_any() is False
    await database_service.user.create(make_user())
    assert await database_service.user.has_any() is True


async def test_get_many_returns_only_requested_existing_users(database_service) -> None:
    alice = await database_service.user.create(make_user())
    bob = await database_service.user.create(make_user(username='bob', email='bob@example.com'))

    result = await database_service.user.get_many({alice.id, bob.id, 'missing'})

    assert result == {alice.id: alice, bob.id: bob}


async def test_list_pending_before_filters_by_status_and_creation_time(database_service) -> None:
    now = datetime.now(timezone.utc)
    expired = await database_service.user.create(make_user(
        username='expired', email='expired@example.com',
        status=UserStatus.PENDING_ACTIVATION, createdAt=now - timedelta(hours=25),
    ))
    await database_service.user.create(make_user(
        username='fresh', email='fresh@example.com',
        status=UserStatus.PENDING_ACTIVATION, createdAt=now,
    ))
    await database_service.user.create(make_user(
        username='active', email='active@example.com',
        status=UserStatus.ACTIVE, createdAt=now - timedelta(hours=25),
    ))

    pending = await database_service.user.list_pending_before(now - timedelta(hours=1))

    assert [user.id for user in pending] == [expired.id]


async def test_username_and_email_uniqueness_are_enforced_by_the_database(database_service) -> None:
    await database_service.user.create(make_user())

    with pytest.raises(DuplicateKeyError):
        await database_service.user.create(make_user(email='someone-else@example.com'))
    with pytest.raises(DuplicateKeyError):
        await database_service.user.create(make_user(username='someone-else'))
