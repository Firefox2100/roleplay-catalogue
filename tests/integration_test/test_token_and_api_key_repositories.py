from datetime import datetime, timedelta, timezone

from roleplay_catalogue.models import ActivationToken, ApiKey, PasswordResetToken


def future(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def past(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


async def test_activation_token_create_is_upsert_by_username(cache_service) -> None:
    first = ActivationToken(username='alice', tokenHash='hash-1', expiresAt=future())
    await cache_service.activation_token.create(first)

    second = ActivationToken(username='alice', tokenHash='hash-2', expiresAt=future())
    await cache_service.activation_token.create(second)

    stored = await cache_service.activation_token.get('alice')
    assert stored.token_hash == 'hash-2'

    assert await cache_service.activation_token.delete('alice') is True
    assert await cache_service.activation_token.get('alice') is None
    assert await cache_service.activation_token.delete('alice') is False


async def test_password_reset_token_create_is_upsert_by_user_id(cache_service) -> None:
    first = PasswordResetToken(userId='user-1', tokenHash='hash-1', expiresAt=future())
    await cache_service.password_reset_token.create(first)

    second = PasswordResetToken(userId='user-1', tokenHash='hash-2', expiresAt=future())
    await cache_service.password_reset_token.create(second)

    stored = await cache_service.password_reset_token.get('user-1')
    assert stored.token_hash == 'hash-2'

    assert await cache_service.password_reset_token.delete('user-1') is True
    assert await cache_service.password_reset_token.get('user-1') is None


async def test_resource_metrics_are_atomic_and_default_to_zero(cache_service) -> None:
    assert (await cache_service.resource_metrics.get('resource-1')).views == 0
    first = await cache_service.resource_metrics.increment_views('resource-1')
    second = await cache_service.resource_metrics.increment_views('resource-1')
    await cache_service.resource_metrics.increment_downloads('resource-1')

    assert first.views == 1
    assert second.views == 2
    metrics = await cache_service.resource_metrics.get_many(['resource-1', 'resource-2'])
    assert metrics['resource-1'].downloads == 1
    assert metrics['resource-2'].views == 0


async def test_api_key_create_get_list_and_delete(database_service) -> None:
    key = await database_service.api_key.create(ApiKey(
        userId='user-1', name='Client', keyHash='hash', expiresAt=future(),
    ))
    other_users_key = await database_service.api_key.create(ApiKey(
        userId='user-2', name='Other', keyHash='hash-2',
    ))

    assert (await database_service.api_key.get(key.id)).id == key.id
    assert [item.id for item in await database_service.api_key.list_for_user('user-1')] == [key.id]

    assert await database_service.api_key.delete(key.id, user_id='user-2') is False
    assert await database_service.api_key.delete(key.id, user_id='user-1') is True
    assert await database_service.api_key.get(key.id) is None
    assert (await database_service.api_key.get(other_users_key.id)) is not None


async def test_delete_for_user_removes_only_that_users_keys(database_service) -> None:
    await database_service.api_key.create(ApiKey(userId='user-1', name='A', keyHash='h1'))
    await database_service.api_key.create(ApiKey(userId='user-1', name='B', keyHash='h2'))
    kept = await database_service.api_key.create(ApiKey(userId='user-2', name='C', keyHash='h3'))

    deleted_count = await database_service.api_key.delete_for_user('user-1')

    assert deleted_count == 2
    assert await database_service.api_key.list_for_user('user-1') == []
    assert (await database_service.api_key.get(kept.id)) is not None


async def test_delete_expired_removes_only_keys_past_their_expiry(database_service) -> None:
    expired = await database_service.api_key.create(ApiKey(
        userId='user-1', name='Expired', keyHash='h1', expiresAt=past(),
    ))
    not_yet_expired = await database_service.api_key.create(ApiKey(
        userId='user-1', name='Fresh', keyHash='h2', expiresAt=future(),
    ))
    never_expires = await database_service.api_key.create(ApiKey(
        userId='user-1', name='Permanent', keyHash='h3',
    ))

    deleted_count = await database_service.api_key.delete_expired(datetime.now(timezone.utc))

    assert deleted_count == 1
    assert await database_service.api_key.get(expired.id) is None
    assert await database_service.api_key.get(not_yet_expired.id) is not None
    assert await database_service.api_key.get(never_expires.id) is not None
