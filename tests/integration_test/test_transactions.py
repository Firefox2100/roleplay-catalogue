import pytest

from roleplay_catalogue.models import User


async def test_transaction_commits_every_write_on_success(database_service) -> None:
    async def operation() -> None:
        await database_service.user.create(User(
            username='alice', email='alice@example.com', passwordHash='hash',
        ))
        await database_service.user.create(User(
            username='bob', email='bob@example.com', passwordHash='hash',
        ))

    await database_service.transaction(operation)

    assert await database_service.user.get_by_username('alice') is not None
    assert await database_service.user.get_by_username('bob') is not None


async def test_transaction_rolls_back_every_write_when_the_operation_raises(
        database_service) -> None:
    class Boom(Exception):
        pass

    async def operation() -> None:
        await database_service.user.create(User(
            username='alice', email='alice@example.com', passwordHash='hash',
        ))
        raise Boom('something went wrong after the first write')

    with pytest.raises(Boom):
        await database_service.transaction(operation)

    assert await database_service.user.get_by_username('alice') is None
