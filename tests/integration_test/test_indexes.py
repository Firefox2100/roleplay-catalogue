import pytest
from pymongo.errors import DuplicateKeyError

from roleplay_catalogue.models import Resource, User
from roleplay_catalogue.services.database.indexes import INDEXES, ensure_indexes


async def test_ensure_indexes_creates_every_defined_index(database_service, mongo_database) -> None:
    by_collection: dict[str, set[str]] = {}
    for definition in INDEXES:
        by_collection.setdefault(definition.collection, set()).add(definition.name)

    for collection_name, expected_names in by_collection.items():
        existing = await mongo_database[collection_name].index_information()
        assert expected_names <= existing.keys()


async def test_ensure_indexes_is_idempotent(database_service, mongo_database) -> None:
    # Runs a second time here; must not raise.
    await ensure_indexes(mongo_database)
    await ensure_indexes(mongo_database)


async def test_unique_indexes_reject_duplicates(database_service, mongo_database) -> None:
    await database_service.user.create(User(
        username='alice', email='alice@example.com', passwordHash='hash',
    ))
    with pytest.raises(DuplicateKeyError):
        await database_service.user.create(User(
            username='alice', email='someone-else@example.com', passwordHash='hash',
        ))

    resource = await database_service.resource.create(Resource(
        resourceType='sillytavern/character', authorId='author', metadata={'name': 'A'},
    ))
    with pytest.raises(DuplicateKeyError):
        await mongo_database['resources'].insert_one(
            resource.model_dump(mode='python', by_alias=True),
        )
