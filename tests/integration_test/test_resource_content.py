from typing import Any

from httpx import ASGITransport, AsyncClient

from roleplay_catalogue.main import app
from roleplay_catalogue.models import Resource, ResourceType, ResourceVersion, User
from roleplay_catalogue.routers.utils import (
    authenticate_user,
    get_database_service,
    get_storage_service,
)


USER = User(
    id='content-author-id',
    username='author',
    email='author@example.com',
    passwordHash='hash',
)
OTHER_USER = User(
    id='other-user-id', username='other', email='other@example.com', passwordHash='hash',
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
                           tags=None, author_id=None, published_resource_ids=None,
                           search_string=None):
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
        if search_string:
            phrase = search_string.casefold()
            resources = [resource for resource in resources if (
                phrase in resource.metadata.name.casefold() or
                phrase in resource.metadata.description.casefold()
            )]
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

    async def get(self, version_id: str) -> ResourceVersion | None:
        return self.documents.get(version_id)

    async def list_for_resource(self, resource_id: str, offset=0, limit=50):
        versions = [version for version in self.documents.values()
                    if version.resource_id == resource_id]
        return sorted(versions, key=lambda version: version.version_number, reverse=True)[offset:offset + limit]

    async def list_by_cover(self, image_resource_id: str):
        return [version for version in self.documents.values()
                if version.cover_image_resource_id == image_resource_id]

    async def delete(self, version_id: str) -> bool:
        return self.documents.pop(version_id, None) is not None

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
        self.silly_tavern_preset_data = MemoryDataRepository()
        self.image_data = MemoryDataRepository()


class MemoryStorageService:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.signed_url_expiry = 120

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def wait_until_available(self, key: str) -> None:
        assert key in self.objects

    async def remove(self, key: str) -> None:
        self.objects.pop(key, None)

    async def fetch(self, key: str):
        yield self.objects[key][0]

    async def create_signed_download_url(self, key: str, file_name: str) -> str:
        return f'https://storage.test/{key}?name={file_name}'


async def authenticated_user() -> User:
    return USER


async def other_authenticated_user() -> User:
    return OTHER_USER


async def get_csrf_headers(client: AsyncClient) -> dict[str, str]:
    token = (await client.get('/auth/csrf')).json()['csrfToken']
    return {'X-CSRF-Token': token}


async def test_character_draft_can_be_added_updated_and_published() -> None:
    database = MemoryDatabaseService()
    storage = MemoryStorageService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[get_storage_service] = lambda: storage
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
                'visibility': 'public',
                'tags': ['catalogue-tag'],
            },
        )
        assert response.status_code == 201
        assert response.json()['authorId'] == USER.id
        assert response.json()['forkedFrom'] is None
        assert response.json()['draftDataId'] is None
        resource_id = response.json()['id']

        response = await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/lorebook', 'name': 'Linked lore',
            'description': 'Shared setting', 'visibility': 'public', 'tags': [],
        })
        assert response.status_code == 201
        linked_lorebook_id = response.json()['id']
        response = await client.put(
            f'/resources/{linked_lorebook_id}/data', headers=headers, json={'data': {
                'name': 'Linked lore', 'entries': [{
                    'keys': ['shared'], 'content': 'Shared linked context', 'enabled': True,
                    'insertion_order': 10, 'use_regex': False, 'constant': False,
                }],
            }},
        )
        assert response.status_code == 200
        response = await client.post(
            f'/versions/{linked_lorebook_id}', headers=headers, json={'version': 'v1.0.0'},
        )
        assert response.status_code == 201
        linked_lorebook_version_id = response.json()['id']
        response = await client.put(f'/resources/{resource_id}', headers=headers, json={
            'name': 'Example character', 'description': 'Catalogue description',
            'visibility': 'public', 'tags': ['catalogue-tag'],
            'linkedLorebooks': [{
                'resourceId': linked_lorebook_id, 'versionId': linked_lorebook_version_id,
            }],
        })
        assert response.status_code == 200
        assert response.json()['linkedLorebooks'][0]['versionId'] == linked_lorebook_version_id

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

        response = await client.get(f'/versions/draft/{resource_id}/download')
        assert response.status_code == 200
        assert b'Character-specific context' in response.content
        assert b'Shared linked context' in response.content

        response = await client.post(
            f'/versions/{resource_id}', headers=headers, json={'version': 'v1.2.3'},
        )
        assert response.status_code == 201
        assert response.json()['versionNumber'] == 1
        assert response.json()['version'] == 'v1.2.3'
        assert response.json()['artifactFileName'] == 'Updated draft.json'
        assert response.json()['linkedLorebooks'][0]['versionId'] == linked_lorebook_version_id
        assert response.json()['linkedLorebooks'][0]['author'] == USER.username
        assert response.json()['dataId'] != draft_id
        snapshot = database.silly_tavern_character_data.documents[response.json()['dataId']]
        assert snapshot.data.creator == USER.username
        assert snapshot.data.description == 'Catalogue description'
        assert snapshot.data.tags == ['catalogue-tag']
        assert snapshot.data.character_version == 'v1.2.3'
        assert len(snapshot.data.character_book.entries) == 1
        artifact_key = response.json()['artifactObjectKey']
        assert storage.objects[artifact_key][1] == 'application/json'
        artifact = storage.objects[artifact_key][0]
        assert b'Character-specific context' in artifact
        assert b'Shared linked context' in artifact
        assert b'"author":"author"' in artifact
        version_id = response.json()['id']

        response = await client.get(f'/versions/{version_id}/data')
        assert response.status_code == 200
        assert response.json()['data']['name'] == 'Updated draft'

        response = await client.get(f'/versions/{version_id}/download')
        assert response.status_code == 200
        assert response.content == storage.objects[artifact_key][0]
        assert "Updated%20draft.json" in response.headers['content-disposition']

        response = await client.get(f'/versions/{version_id}/signed-download')
        assert response.status_code == 200
        assert response.json()['expiresIn'] == 120
        assert response.json()['url'].startswith('https://storage.test/releases/')

        response = await client.post(f'/versions/{version_id}/fork', headers=headers)
        assert response.status_code == 201
        fork = response.json()
        assert fork['metadata']['name'] == 'Forked from Example character'
        assert fork['metadata']['visibility'] == 'private'
        assert fork['forkedFrom'] == {'resourceId': resource_id, 'versionId': version_id, 'instance': None}
        fork_draft = database.silly_tavern_character_data.documents[fork['draftDataId']]
        assert fork_draft.resource_version_id is None
        assert fork_draft.data.name == 'Updated draft'

        response = await client.get(f'/versions/draft/{resource_id}/download')
        assert response.status_code == 200
        assert response.json()['data']['name'] == 'Updated draft'
        assert "Updated%20draft.draft.json" in response.headers['content-disposition']

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


async def test_lorebook_import_export_publish_and_fork() -> None:
    database = MemoryDatabaseService()
    storage = MemoryStorageService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[authenticate_user] = authenticated_user
    lorebook_json = b'''{
      "spec": "lorebook_v3",
      "data": {
        "name": "Imported title",
        "description": "Imported lore description",
        "extensions": {},
        "entries": [{
          "keys": ["castle"], "content": "An ancient castle.", "extensions": {},
          "enabled": true, "insertion_order": 5, "use_regex": false, "constant": false
        }]
      }
    }'''

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = await get_csrf_headers(client)
        response = await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/lorebook', 'name': 'Castle lore',
            'description': '', 'visibility': 'public', 'tags': ['fantasy'],
        })
        assert response.status_code == 201
        resource_id = response.json()['id']

        response = await client.post(
            f'/resources/{resource_id}/import-lorebook', headers=headers,
            files={'file': ('lore.json', lorebook_json, 'application/json')},
        )
        assert response.status_code == 200
        assert response.json()['draft']['data']['entries'][0]['content'] == 'An ancient castle.'
        assert response.json()['resource']['metadata']['description'] == 'Imported lore description'

        response = await client.get(f'/versions/draft/{resource_id}/download')
        assert response.status_code == 200
        assert response.json()['spec'] == 'lorebook_v3'
        assert response.json()['data']['name'] == 'Castle lore'
        assert response.headers['content-type'].startswith('application/json')

        response = await client.post(
            f'/versions/{resource_id}', headers=headers, json={'version': 'first edition'},
        )
        assert response.status_code == 201
        version = response.json()
        assert version['artifactContentType'] == 'application/json'
        assert version['artifactFileName'] == 'Castle lore.json'
        assert version['coverImageResourceId'] is None
        snapshot = database.silly_tavern_lorebook_data.documents[version['dataId']]
        assert snapshot.data.name == 'Castle lore'
        assert snapshot.data.description == 'Imported lore description'

        artifact = storage.objects[version['artifactObjectKey']][0]
        assert b'"spec":"lorebook_v3"' in artifact

        response = await client.post(f'/versions/{version["id"]}/fork', headers=headers)
        assert response.status_code == 201
        fork = response.json()
        assert fork['resourceType'] == 'sillytavern/lorebook'
        assert fork['metadata']['name'] == 'Forked from Castle lore'
        fork_draft = database.silly_tavern_lorebook_data.documents[fork['draftDataId']]
        assert fork_draft.resource_version_id is None
        assert fork_draft.data.entries[0].keys == ['castle']


async def test_preset_import_export_publish_and_fork() -> None:
    database = MemoryDatabaseService()
    storage = MemoryStorageService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[authenticate_user] = authenticated_user
    preset_json = b'''{
      "temperature": 0.75, "top_p": 0.9, "openrouter_model": "example/model",
      "prompts": [{"identifier": "main", "name": "Main", "role": "system", "content": "Write vividly."}],
      "prompt_order": [{"character_id": 100000, "order": [{"identifier": "main", "enabled": true}]}]
    }'''

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = await get_csrf_headers(client)
        response = await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/preset', 'name': 'Vivid preset',
            'description': 'Chat preset', 'visibility': 'public', 'tags': ['writing'],
        })
        assert response.status_code == 201
        resource_id = response.json()['id']
        response = await client.post(
            f'/resources/{resource_id}/import-preset', headers=headers,
            files={'file': ('preset.json', preset_json, 'application/json')},
        )
        assert response.status_code == 200
        assert response.json()['draft']['data']['openrouter_model'] == 'example/model'

        response = await client.get(f'/versions/draft/{resource_id}/download')
        assert response.status_code == 200
        assert response.json()['prompts'][0]['content'] == 'Write vividly.'

        response = await client.post(f'/versions/{resource_id}', headers=headers, json={'version': 'v1'})
        assert response.status_code == 201
        version = response.json()
        assert b'example/model' in storage.objects[version['artifactObjectKey']][0]

        response = await client.post(f"/versions/{version['id']}/fork", headers=headers)
        assert response.status_code == 201
        fork = response.json()
        assert fork['resourceType'] == 'sillytavern/preset'
        assert database.silly_tavern_preset_data.documents[fork['draftDataId']].data.temperature == 0.75


async def test_character_fork_requires_access_to_the_release() -> None:
    database = MemoryDatabaseService()
    storage = MemoryStorageService()
    resource = Resource(
        id='private-source', resourceType=ResourceType.SILLY_TAVERN_CHARACTER,
        authorId=USER.id, metadata={'name': 'Private source', 'visibility': 'private'},
    )
    await database.resource.create(resource)
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[authenticate_user] = authenticated_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = await get_csrf_headers(client)
        response = await client.put(
            f'/resources/{resource.id}/data', headers=headers, json={'data': {'name': 'Secret'}},
        )
        assert response.status_code == 200
        response = await client.post(
            f'/versions/{resource.id}', headers=headers, json={'version': 'private release'},
        )
        assert response.status_code == 201
        version_id = response.json()['id']

        app.dependency_overrides[authenticate_user] = other_authenticated_user
        response = await client.post(f'/versions/{version_id}/fork', headers=headers)

        assert response.status_code == 404

    assert len(database.resource.documents) == 1


async def test_character_can_link_foreign_lorebook_release_but_not_publish_draft_link() -> None:
    database = MemoryDatabaseService()
    database.user.documents[OTHER_USER.id] = OTHER_USER
    storage = MemoryStorageService()
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[authenticate_user] = other_authenticated_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = await get_csrf_headers(client)
        lorebook = (await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/lorebook', 'name': 'Other world',
            'description': '', 'visibility': 'public', 'tags': [],
        })).json()
        await client.put(f"/resources/{lorebook['id']}/data", headers=headers, json={'data': {
            'entries': [{'keys': ['world'], 'content': 'Foreign lore', 'enabled': True,
                         'insertion_order': 0, 'use_regex': False, 'constant': False}],
        }})
        lorebook_version = (await client.post(
            f"/versions/{lorebook['id']}", headers=headers, json={'version': 'shared-v1'},
        )).json()

        app.dependency_overrides[authenticate_user] = authenticated_user
        headers = await get_csrf_headers(client)
        character = (await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/character', 'name': 'Uses shared world',
            'description': '', 'visibility': 'public', 'tags': [],
        })).json()
        await client.put(f"/resources/{character['id']}/data", headers=headers,
                         json={'data': {'name': 'Uses shared world'}})
        response = await client.put(f"/resources/{character['id']}", headers=headers, json={
            'name': 'Uses shared world', 'description': '', 'visibility': 'public', 'tags': [],
            'linkedLorebooks': [{'resourceId': lorebook['id'], 'versionId': lorebook_version['id']}],
        })
        assert response.status_code == 200
        response = await client.post(
            f"/versions/{character['id']}", headers=headers, json={'version': 'v1'},
        )
        assert response.status_code == 201
        assert response.json()['linkedLorebooks'][0]['author'] == OTHER_USER.username
        assert b'"author":"other"' in storage.objects[response.json()['artifactObjectKey']][0]

        own_lorebook = (await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/lorebook', 'name': 'Unreleased draft',
            'description': '', 'visibility': 'private', 'tags': [],
        })).json()
        await client.put(f"/resources/{own_lorebook['id']}/data", headers=headers,
                         json={'data': {'entries': []}})
        draft_character = (await client.post('/resources', headers=headers, json={
            'resourceType': 'sillytavern/character', 'name': 'Draft linked',
            'description': '', 'visibility': 'private', 'tags': [],
        })).json()
        await client.put(f"/resources/{draft_character['id']}/data", headers=headers,
                         json={'data': {'name': 'Draft linked'}})
        await client.put(f"/resources/{draft_character['id']}", headers=headers, json={
            'name': 'Draft linked', 'description': '', 'visibility': 'private', 'tags': [],
            'linkedLorebooks': [{'resourceId': own_lorebook['id'], 'versionId': None}],
        })
        response = await client.post(
            f"/versions/{draft_character['id']}", headers=headers, json={'version': 'v1'},
        )
        assert response.status_code == 409
        assert 'cannot link lorebook drafts' in response.json()['detail']
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
    special_name = Resource(
        id='special-name', resourceType=ResourceType.SILLY_TAVERN_CHARACTER,
        authorId=USER.id,
        metadata={'name': 'Mage [v2] hero', 'visibility': 'public', 'tags': ['magic']},
    )
    for resource in (matching, wrong_type, private, special_name):
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
    assert [resource['id'] for resource in response.json()['items']] == [matching.id]
    assert response.json()['nextOffset'] is None

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/resources', params={'publishedOnly': 'true'})
        assert response.json() == {'items': [], 'nextOffset': None}

        await database.resource_version.create(ResourceVersion(
            resourceId=matching.id,
            resourceType=matching.resource_type,
            versionNumber=1,
            dataId='snapshot-id',
            metadata=matching.metadata,
            publishedById=USER.id,
        ))
        response = await client.get('/resources', params={'publishedOnly': 'true'})
        assert [resource['id'] for resource in response.json()['items']] == [matching.id]

        response = await client.get('/resources/tags', params={'search': 'port'})
        assert response.json() == ['portrait']

        response = await client.get('/resources', params={'search_string': '[v2] hero'})
        assert [resource['id'] for resource in response.json()['items']] == [special_name.id]


async def test_resource_listing_exposes_next_offset_and_updates_visibility() -> None:
    database = MemoryDatabaseService()
    first = Resource(
        id='first', resourceType=ResourceType.SILLY_TAVERN_CHARACTER, authorId=USER.id,
        metadata={'name': 'First', 'visibility': 'public'},
    )
    second = Resource(
        id='second', resourceType=ResourceType.SILLY_TAVERN_CHARACTER, authorId=USER.id,
        metadata={'name': 'Second', 'visibility': 'public'},
    )
    await database.resource.create(first)
    await database.resource.create(second)
    app.dependency_overrides[get_database_service] = lambda: database
    app.dependency_overrides[authenticate_user] = authenticated_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        page = await client.get('/resources', params={'limit': 1})
        assert len(page.json()['items']) == 1
        assert page.json()['nextOffset'] == 1

        headers = await get_csrf_headers(client)
        response = await client.put(
            f'/resources/{first.id}', headers=headers,
            json={'name': 'First', 'description': '', 'visibility': 'private', 'tags': []},
        )

    assert response.status_code == 200
    assert response.json()['metadata']['visibility'] == 'private'


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
