from typing import Any

from httpx import ASGITransport, AsyncClient

from roleplay_catalogue.main import app
from roleplay_catalogue.models import Resource, ResourceVersion, User
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


class MemoryVersionRepository:
    def __init__(self):
        self.documents: dict[str, ResourceVersion] = {}

    async def create(self, version: ResourceVersion) -> ResourceVersion:
        self.documents[version.id] = version
        return version

    async def get_latest(self, resource_id: str) -> ResourceVersion | None:
        versions = [
            version for version in self.documents.values()
            if version.resource_id == resource_id
        ]
        return max(versions, key=lambda version: version.version_number) if versions else None


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
            json={'data': {'name': 'Updated draft'}},
        )
        assert response.status_code == 200
        assert response.json()['id'] == draft_id
        assert response.json()['data']['name'] == 'Updated draft'

        response = await client.post(f'/versions/{resource_id}', headers=headers)
        assert response.status_code == 201
        assert response.json()['versionNumber'] == 1
        assert response.json()['dataId'] != draft_id

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
