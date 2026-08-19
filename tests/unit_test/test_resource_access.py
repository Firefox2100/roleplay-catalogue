import pytest
from fastapi import HTTPException

from roleplay_catalogue.misc import ResourceType, ResourceVisibility
from roleplay_catalogue.models import Resource, ResourceMetadata, ResourceVersion, User
from roleplay_catalogue.components import (
    can_read_resource,
    get_data_repository,
    get_editable_resource,
    get_owned_resource,
    get_readable_resource,
    get_readable_version,
    is_resource_editor,
    resource_editor_ids,
)


AUTHOR = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')
CO_AUTHOR = User(
    id='co-author-id', username='co-author', email='co@example.com', passwordHash='hash',
)
STRANGER = User(
    id='stranger-id', username='stranger', email='stranger@example.com', passwordHash='hash',
)


def make_resource(visibility: ResourceVisibility,
                  resource_type: ResourceType = ResourceType.SILLY_TAVERN_CHARACTER,
                  ) -> Resource:
    return Resource(
        resourceType=resource_type,
        authorId=AUTHOR.id,
        coAuthorIds=(CO_AUTHOR.id,),
        metadata=ResourceMetadata(name='Example', visibility=visibility),
    )


def test_resource_editor_ids_includes_author_and_co_authors() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert resource_editor_ids(resource) == frozenset({AUTHOR.id, CO_AUTHOR.id})


def test_is_resource_editor_true_for_author_and_co_author_only() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert is_resource_editor(resource, AUTHOR) is True
    assert is_resource_editor(resource, CO_AUTHOR) is True
    assert is_resource_editor(resource, STRANGER) is False
    assert is_resource_editor(resource, None) is False


def test_co_author_can_read_a_private_resource_like_the_author() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert can_read_resource(resource, CO_AUTHOR) is True
    assert can_read_resource(resource, STRANGER) is False
    assert can_read_resource(resource, None) is False


def test_public_and_authenticated_visibility_are_unaffected_by_co_authoring() -> None:
    public = make_resource(ResourceVisibility.PUBLIC)
    authenticated = make_resource(ResourceVisibility.AUTHENTICATED)

    assert can_read_resource(public, None) is True
    assert can_read_resource(public, STRANGER) is True
    assert can_read_resource(authenticated, None) is False
    assert can_read_resource(authenticated, STRANGER) is True


class Repo:
    def __init__(self, documents=()):
        self.documents = {document.id: document for document in documents}

    async def get(self, item_id):
        return self.documents.get(item_id)


class FakeDatabase:
    def __init__(self, resources=(), versions=()):
        self.resource = Repo(resources)
        self.resource_version = Repo(versions)


async def test_get_readable_resource_404s_when_missing_or_unreadable() -> None:
    private = make_resource(ResourceVisibility.PRIVATE)
    database = FakeDatabase(resources=[private])

    assert await get_readable_resource(database, private.id, AUTHOR) == private
    with pytest.raises(HTTPException) as excinfo:
        await get_readable_resource(database, private.id, STRANGER)
    assert excinfo.value.status_code == 404
    with pytest.raises(HTTPException) as excinfo:
        await get_readable_resource(database, 'missing-id', AUTHOR)
    assert excinfo.value.status_code == 404


async def test_get_owned_resource_is_author_only() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)
    database = FakeDatabase(resources=[resource])

    assert await get_owned_resource(database, resource.id, AUTHOR) == resource
    with pytest.raises(HTTPException) as excinfo:
        await get_owned_resource(database, resource.id, CO_AUTHOR)
    assert excinfo.value.status_code == 404
    with pytest.raises(HTTPException) as excinfo:
        await get_owned_resource(database, resource.id, STRANGER)
    assert excinfo.value.status_code == 404


async def test_get_owned_resource_rejects_a_type_mismatch() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE, ResourceType.SILLY_TAVERN_LOREBOOK)
    database = FakeDatabase(resources=[resource])

    with pytest.raises(HTTPException) as excinfo:
        await get_owned_resource(
            database, resource.id, AUTHOR, expected_type=ResourceType.SILLY_TAVERN_CHARACTER,
        )
    assert excinfo.value.status_code == 409


async def test_get_editable_resource_allows_author_and_co_author_only() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)
    database = FakeDatabase(resources=[resource])

    assert await get_editable_resource(database, resource.id, AUTHOR) == resource
    assert await get_editable_resource(database, resource.id, CO_AUTHOR) == resource
    with pytest.raises(HTTPException) as excinfo:
        await get_editable_resource(database, resource.id, STRANGER)
    assert excinfo.value.status_code == 404


async def test_get_editable_resource_rejects_a_type_mismatch() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE, ResourceType.SILLY_TAVERN_LOREBOOK)
    database = FakeDatabase(resources=[resource])

    with pytest.raises(HTTPException) as excinfo:
        await get_editable_resource(
            database, resource.id, AUTHOR, expected_type=ResourceType.SILLY_TAVERN_CHARACTER,
        )
    assert excinfo.value.status_code == 409


def make_version(resource: Resource, visibility: ResourceVisibility) -> ResourceVersion:
    return ResourceVersion(
        resourceId=resource.id, resourceType=resource.resource_type, versionNumber=1,
        dataId='data-id', metadata=resource.metadata, visibility=visibility,
        publishedById=AUTHOR.id,
    )


async def test_get_readable_version_lets_editors_bypass_visibility() -> None:
    resource = make_resource(ResourceVisibility.PUBLIC)
    version = make_version(resource, ResourceVisibility.PRIVATE)
    database = FakeDatabase(resources=[resource], versions=[version])

    assert await get_readable_version(database, version.id, AUTHOR) == version
    assert await get_readable_version(database, version.id, CO_AUTHOR) == version


async def test_get_readable_version_hides_private_versions_from_non_editors() -> None:
    resource = make_resource(ResourceVisibility.PUBLIC)
    version = make_version(resource, ResourceVisibility.PRIVATE)
    database = FakeDatabase(resources=[resource], versions=[version])

    with pytest.raises(HTTPException) as excinfo:
        await get_readable_version(database, version.id, STRANGER)
    assert excinfo.value.status_code == 404
    with pytest.raises(HTTPException) as excinfo:
        await get_readable_version(database, version.id, None)
    assert excinfo.value.status_code == 404


async def test_get_readable_version_requires_authentication_for_authenticated_visibility() -> None:
    resource = make_resource(ResourceVisibility.PUBLIC)
    version = make_version(resource, ResourceVisibility.AUTHENTICATED)
    database = FakeDatabase(resources=[resource], versions=[version])

    with pytest.raises(HTTPException) as excinfo:
        await get_readable_version(database, version.id, None)
    assert excinfo.value.status_code == 404
    assert await get_readable_version(database, version.id, STRANGER) == version


async def test_get_readable_version_is_visible_to_anyone_when_public() -> None:
    resource = make_resource(ResourceVisibility.PUBLIC)
    version = make_version(resource, ResourceVisibility.PUBLIC)
    database = FakeDatabase(resources=[resource], versions=[version])

    assert await get_readable_version(database, version.id, None) == version
    assert await get_readable_version(database, version.id, STRANGER) == version


async def test_get_readable_version_404s_when_version_or_resource_is_missing() -> None:
    database = FakeDatabase()

    with pytest.raises(HTTPException) as excinfo:
        await get_readable_version(database, 'missing-version', STRANGER)
    assert excinfo.value.status_code == 404

    resource = make_resource(ResourceVisibility.PUBLIC)
    orphan_version = ResourceVersion(
        resourceId='missing-resource', resourceType=resource.resource_type, versionNumber=1,
        dataId='data-id', metadata=resource.metadata, publishedById=AUTHOR.id,
    )
    database = FakeDatabase(versions=[orphan_version])
    with pytest.raises(HTTPException) as excinfo:
        await get_readable_version(database, orphan_version.id, STRANGER)
    assert excinfo.value.status_code == 404


def test_get_data_repository_resolves_every_resource_type() -> None:
    class FakeDatabaseWithRepos:
        silly_tavern_character_data = 'character-repo'
        silly_tavern_lorebook_data = 'lorebook-repo'
        silly_tavern_preset_data = 'preset-repo'
        image_data = 'image-repo'
        world_data = 'world-repo'

    database = FakeDatabaseWithRepos()

    assert get_data_repository(database, ResourceType.SILLY_TAVERN_CHARACTER) == 'character-repo'
    assert get_data_repository(database, ResourceType.SILLY_TAVERN_LOREBOOK) == 'lorebook-repo'
    assert get_data_repository(database, ResourceType.SILLY_TAVERN_PRESET) == 'preset-repo'
    assert get_data_repository(database, ResourceType.IMAGE) == 'image-repo'
    assert get_data_repository(database, ResourceType.WORLD_SIMULATION_WORLD) == 'world-repo'
