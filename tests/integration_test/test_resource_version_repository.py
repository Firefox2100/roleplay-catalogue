import pytest
from pymongo.errors import DuplicateKeyError

from roleplay_catalogue.misc import ResourceType
from roleplay_catalogue.models import ResourceVersion


def make_version(**overrides) -> ResourceVersion:
    defaults = {
        'resourceId': 'resource-id', 'resourceType': ResourceType.SILLY_TAVERN_CHARACTER,
        'versionNumber': 1, 'dataId': 'data-id', 'metadata': {'name': 'Example'},
        'publishedById': 'author-id',
    }
    return ResourceVersion(**{**defaults, **overrides})


async def test_create_get_update_and_delete_round_trip(database_service) -> None:
    version = await database_service.resource_version.create(make_version())

    fetched = await database_service.resource_version.get(version.id)
    assert fetched.id == version.id
    assert await database_service.resource_version.get('missing') is None

    updated = fetched.model_copy(update={'version': 'v2'})
    await database_service.resource_version.update(updated)
    assert (await database_service.resource_version.get(version.id)).version == 'v2'

    assert await database_service.resource_version.delete(version.id) is True
    assert await database_service.resource_version.get(version.id) is None
    assert await database_service.resource_version.delete(version.id) is False


async def test_get_latest_picks_the_highest_version_number(database_service) -> None:
    await database_service.resource_version.create(make_version(versionNumber=1, dataId='d1'))
    latest = await database_service.resource_version.create(make_version(versionNumber=3, dataId='d3'))
    await database_service.resource_version.create(make_version(versionNumber=2, dataId='d2'))

    assert (await database_service.resource_version.get_latest('resource-id')).id == latest.id
    assert await database_service.resource_version.get_latest('missing-resource') is None


async def test_list_for_resource_orders_newest_first_and_paginates(database_service) -> None:
    for number in range(1, 4):
        await database_service.resource_version.create(
            make_version(versionNumber=number, dataId=f'd{number}'),
        )

    all_versions = await database_service.resource_version.list_for_resource('resource-id')
    assert [version.version_number for version in all_versions] == [3, 2, 1]

    page = await database_service.resource_version.list_for_resource('resource-id', offset=1, limit=1)
    assert [version.version_number for version in page] == [2]


async def test_list_all_for_resource_and_exists_for_resource(database_service) -> None:
    assert await database_service.resource_version.exists_for_resource('resource-id') is False

    await database_service.resource_version.create(make_version(versionNumber=1, dataId='d1'))
    await database_service.resource_version.create(make_version(versionNumber=2, dataId='d2'))

    assert await database_service.resource_version.exists_for_resource('resource-id') is True
    all_versions = await database_service.resource_version.list_all_for_resource('resource-id')
    assert {version.version_number for version in all_versions} == {1, 2}


async def test_list_by_cover_returns_versions_using_that_image(database_service) -> None:
    matching = await database_service.resource_version.create(
        make_version(coverImageResourceId='cover-1'),
    )
    await database_service.resource_version.create(
        make_version(versionNumber=2, dataId='d2', coverImageResourceId='cover-2'),
    )

    results = await database_service.resource_version.list_by_cover('cover-1')

    assert [version.id for version in results] == [matching.id]


async def test_list_published_resource_ids_is_distinct_across_versions(database_service) -> None:
    await database_service.resource_version.create(make_version(versionNumber=1, dataId='d1'))
    await database_service.resource_version.create(make_version(versionNumber=2, dataId='d2'))
    await database_service.resource_version.create(
        make_version(resourceId='other-resource', versionNumber=1, dataId='d3'),
    )

    ids = await database_service.resource_version.list_published_resource_ids()

    assert set(ids) == {'resource-id', 'other-resource'}


async def test_resource_and_version_number_uniqueness_is_enforced(database_service) -> None:
    await database_service.resource_version.create(make_version(versionNumber=1, dataId='d1'))

    with pytest.raises(DuplicateKeyError):
        await database_service.resource_version.create(make_version(versionNumber=1, dataId='d2'))
