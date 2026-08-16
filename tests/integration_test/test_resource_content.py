from typing import Any

from httpx import ASGITransport, AsyncClient

from roleplay_catalogue.main import app
from roleplay_catalogue.models import Resource, ResourceType, ResourceVersion, User
from roleplay_catalogue.routers.utils import authenticate_user, get_database_service


USER = User(
    id='content-author-id',
    username='author',
    email='author@example.com',
    passwordHash='hash',
)


class MemoryResourceRepository:
    def __init__(self):
        self.documents: dict[str, Resource] = {}

    async def create(self, resource: Resource) -> Resource:
        self.documents[resource.id] = resource
        return resource

    async def get(self, resource_id: str) -> Resource | None:
        return self.documents.get(resource_id)

    async def update(self, resource: Resource) -> Resource:
        self.documents[resource.id] = resource
        return resource

    async def list_visible(self, user_id, offset=0, limit=50, resource_type=None,
                           tags=None, author_id=None, published_resource_ids=None):
        resources = list(self.documents.values())
        resources = [resource for resource in resources if (
            resource.metadata.visibility.value == 'public' or resource.author_id == user_id
        )]
        if resource_type:
            resources = [resource for resource in resources if resource.resource_type == resource_type]
        if tags:
            resources = [resource for resource in resources if set(tags) <= set(resource.metadata.tags)]
        if author_id:
            resources = [resource for resource in resources if resource.author_id == author_id]
        if published_resource_ids is not None:
            resources = [resource for resource in resources if resource.id in published_resource_ids]
        return resources[offset:offset + limit]

    async def suggest_tags(self, user_id, search, limit=10):
        tags = {
            tag for resource in self.documents.values()
            for tag in resource.metadata.tags
            if search.casefold() in tag.casefold()
        }
        return sorted(tags)[:limit]


class MemoryUserRepository:
    def __init__(self):
        self.documents = {USER.id: USER}

    async def get(self, user_id: str):
        return self.documents.get(user_id)

    async def get_by_username(self, username: str):
        return next((user for user in self.documents.values() if user.username == username), None)

    async def get_many(self, user_ids: set[str]):
        return {user_id: self.documents[user_id] for user_id in user_ids if user_id in self.documents}


class MemoryVersionRepository:
    def __init__(self):
        self.documents: dict[str, ResourceVersion] = {}

    async def create(self, version: ResourceVersion) -> ResourceVersion:
        self.documents[version.id] = version
        return version

    async def update(self, version: ResourceVersion) -> ResourceVersion:
        self.documents[version.id] = version
        return version

    async def get_latest(self, resource_id: str) -> ResourceVersion | None:
        versions = [
            version for version in self.documents.values()
            if version.resource_id == resource_id
        ]
        return max(versions, key=lambda version: version.version_number) if versions else None

    async def list_published_resource_ids(self) -> list[str]:
        return list({version.resource_id for version in self.documents.values()})


class MemoryDataRepository:
    def __init__(self):
        self.documents: dict[str, Any] = {}

    async def create(self, document):
        self.documents[document.id] = document
        return document

    async def get(self, data_id: str):
        return self.documents.get(data_id)

    async def update(self, document):
        self.documents[document.id] = document
        return document

    async def delete(self, data_id: str) -> bool:
        return self.documents.pop(data_id, None) is not None


class MemoryDatabaseService:
    def __init__(self):
        self.user = MemoryUserRepository()
        self.resource = MemoryResourceRepository()
        self.resource_version = MemoryVersionRepository()
        self.silly_tavern_character_data = MemoryDataRepository()
        self.silly_tavern_lorebook_data = MemoryDataRepository()
        self.image_data = MemoryDataRepository()


async def authenticated_user() -> User:
    return USER


async def get_csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = (await client.get('/auth/csrf')).json()['csrfToken']
    return {'X-CSRF-Token': token}


async def test_character_draft_can_be_added_updated_and_published() -> None:
    database = MemoryDatabaseService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[authenticate_user] = authenticated_user

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
    ) as client:
        headers = await get_csrf_headers(client)
        response = await client.post(
            '/resources',
            headers=headers,
            json={
                'resourceType': 'sillytavern/character',
                'name': 'Example character',
                'description': 'Catalogue description',
                'tags': ['catalogue-tag'],
            },
        )
        assert response.status_code == 201
        assert response.json()['authorId'] == USER.id
        assert response.json()['forkedFrom'] is None
        assert response.json()['draftDataId'] is None
        resource_id = response.json()['id']

        response = await client.put(
            f'/resources/{resource_id}/data',
            headers=headers,
            json={'data': {'name': 'First draft'}},
        )
        assert response.status_code == 200
        draft_id = response.json()['id']

        response = await client.put(
            f'/resources/{resource_id}/data',
            headers=headers,
            json={'data': {
                'name': 'Updated draft',
                'character_book': {
                    'name': 'Embedded lore',
                    'entries': [{
                        'keys': ['example'],
                        'content': 'Character-specific context',
                        'enabled': True,
                        'insertion_order': 0,
                        'use_regex': False,
                        'constant': False,
                    }],
                },
            }},
        )
        assert response.status_code == 200
        assert response.json()['id'] == draft_id
        assert response.json()['data']['name'] == 'Updated draft'
        assert response.json()['data']['character_book']['entries'][0]['content'] == (
            'Character-specific context'
        )

        response = await client.post(f'/versions/{resource_id}', headers=headers)
        assert response.status_code == 201
        assert response.json()['versionNumber'] == 1
        assert response.json()['dataId'] != draft_id
        snapshot = database.silly_tavern_character_data.documents[response.json()['dataId']]
        assert snapshot.data.creator == USER.username
        assert snapshot.data.description == 'Catalogue description'
        assert snapshot.data.tags == ['catalogue-tag']

        response = await client.get(f'/resources/{resource_id}/data')
        assert response.status_code == 200
        assert response.json()['data']['name'] == 'Updated draft'


async def test_resource_data_is_validated_for_its_resource_type() -> None:
    database = MemoryDatabaseService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[authenticate_user] = authenticated_user

    resource = Resource(
        id='image-resource-id',
        resourceType='core/image',
        authorId=USER.id,
        metadata={'name': 'Image'},
    )
    await database.resource.create(resource)

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
    ) as client:
        headers = await get_csrf_headers(client)
        response = await client.put(
            f'/resources/{resource.id}/data',
            headers=headers,
            json={'data': {'name': 'Not image metadata'}},
        )
        assert response.status_code == 422


async def test_resource_listing_filters_by_type_tags_and_author_username() -> None:
    database = MemoryDatabaseService()
    matching = Resource(
        id='matching-resource', resourceType=ResourceType.SILLY_TAVERN_CHARACTER,
        authorId=USER.id,
        metadata={'name': 'Matching', 'visibility': 'public', 'tags': ['fantasy', 'portrait']},
    )
    wrong_type = Resource(
        id='wrong-type', resourceType=ResourceType.SILLY_TAVERN_LOREBOOK,
        authorId=USER.id,
        metadata={'name': 'Lorebook', 'visibility': 'public', 'tags': ['fantasy', 'portrait']},
    )
    private = Resource(
        id='private-resource', resourceType=ResourceType.SILLY_TAVERN_CHARACTER,
        authorId=USER.id,
        metadata={'name': 'Private', 'visibility': 'private', 'tags': ['fantasy', 'portrait']},
    )
    for resource in (matching, wrong_type, private):
        await database.resource.create(resource)
    app.dependency_overrides[get_database_service] = lambda: database

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/resources', params=[
            ('resourceType', 'sillytavern/character'),
            ('tags', 'fantasy'),
            ('tags', 'portrait'),
            ('author', USER.username),
        ])

    assert response.status_code == 200
    assert [resource['id'] for resource in response.json()] == [matching.id]

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/resources', params={'publishedOnly': 'true'})
        assert response.json() == []

        await database.resource_version.create(ResourceVersion(
            resourceId=matching.id,
            resourceType=matching.resource_type,
            versionNumber=1,
            dataId='snapshot-id',
            metadata=matching.metadata,
            publishedById=USER.id,
        ))
        response = await client.get('/resources', params={'publishedOnly': 'true'})
        assert [resource['id'] for resource in response.json()] == [matching.id]

        response = await client.get('/resources/tags', params={'search': 'port'})
        assert response.json() == ['portrait']


async def test_image_metadata_and_sole_version_are_updated_together() -> None:
    database = MemoryDatabaseService()
    image = Resource(
        id='editable-image', resourceType=ResourceType.IMAGE, authorId=USER.id,
        metadata={'name': 'Original image', 'visibility': 'private'},
    )
    version = ResourceVersion(
        id='image-version', resourceId=image.id, resourceType=ResourceType.IMAGE,
        versionNumber=1, dataId='image-data', metadata=image.metadata, publishedById=USER.id,
    )
    await database.resource.create(image)
    await database.resource_version.create(version)
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[authenticate_user] = authenticated_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = await get_csrf_headers(client)
        response = await client.put(
            f'/images/{image.id}/metadata',
            headers=headers,
            json={
                'name': 'Renamed image',
                'description': 'Updated description',
                'visibility': 'public',
                'tags': ['cover'],
            },
        )

    assert response.status_code == 200
    assert response.json()['metadata']['visibility'] == 'public'
    assert database.resource_version.documents[version.id].metadata.name == 'Renamed image'
