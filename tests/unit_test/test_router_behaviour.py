from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import Headers, UploadFile

from roleplay_catalogue.models import (
    ImageData,
    ImageDataDocument,
    Resource,
    ResourceType,
    ResourceVersion,
    User,
)
from roleplay_catalogue.routers.image_data import (
    create_image_data,
    delete_image_data,
    get_image_data,
    list_image_data,
)
from roleplay_catalogue.routers.images import image_response
from roleplay_catalogue.routers.worlds import import_world_bundle
from roleplay_catalogue.main import SPAStaticFiles, duplicate_key_error_handler
from roleplay_catalogue.routers.utils import (
    authenticate_api_key,
    authenticate_session_user,
    authenticate_user,
    optionally_authenticate_user,
)
from roleplay_catalogue.misc import UserCredentialMismatch


AUTHOR = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')


def image_resource(*, draft_data_id=None) -> Resource:
    return Resource(
        id='image-id', resourceType=ResourceType.IMAGE, authorId=AUTHOR.id,
        draftDataId=draft_data_id, metadata={'name': 'Image'},
    )


def image_document(*, published=False) -> ImageDataDocument:
    return ImageDataDocument(
        id='data-id', resourceId='image-id',
        resourceVersionId='version-id' if published else None,
        objectKey='images/data.png', contentType='image/png', byteSize=3,
        sha256='a' * 64, width=1, height=1,
    )


class DataRepository:
    def __init__(self, documents=()):
        self.documents = {document.id: document for document in documents}

    async def create(self, document):
        self.documents[document.id] = document
        return document

    async def get(self, data_id):
        return self.documents.get(data_id)

    async def list_for_resource(self, resource_id):
        return [item for item in self.documents.values() if item.resource_id == resource_id]

    async def delete(self, data_id):
        return self.documents.pop(data_id, None) is not None


class ResourceRepository:
    def __init__(self, resource):
        self.resource = resource

    async def get(self, resource_id):
        return self.resource if self.resource.id == resource_id else None

    async def update(self, resource):
        self.resource = resource
        return resource


class ImageDatabase:
    def __init__(self, resource, documents=(), *, has_version=False):
        self.resource = ResourceRepository(resource)
        self.image_data = DataRepository(documents)
        self.resource_version = SimpleNamespace(
            exists_for_resource=AsyncMock(return_value=has_version),
            get_latest=AsyncMock(return_value=None),
        )

    async def transaction(self, operation):
        return await operation()


async def test_image_data_draft_lifecycle(monkeypatch) -> None:
    database = ImageDatabase(image_resource())
    monkeypatch.setattr(
        'roleplay_catalogue.routers.image_data.get_editable_resource',
        AsyncMock(side_effect=lambda *_args: database.resource.resource),
    )
    payload = ImageData(
        objectKey='images/data.png', contentType='image/png', byteSize=3,
        sha256='a' * 64, width=1, height=1,
    )

    created = await create_image_data('image-id', payload, database, AUTHOR)
    assert database.resource.resource.draft_data_id == created.id
    assert await list_image_data('image-id', database, AUTHOR) == [created]
    assert await get_image_data(created.id, database, AUTHOR) == created

    await delete_image_data(created.id, database, AUTHOR)
    assert database.resource.resource.draft_data_id is None
    assert not database.image_data.documents


@pytest.mark.parametrize('draft_data_id,has_version,detail', [
    ('existing', False, 'already has image data'),
    (None, True, 'immutable'),
])
async def test_image_data_creation_rejects_existing_content(
        monkeypatch, draft_data_id, has_version, detail,
) -> None:
    database = ImageDatabase(image_resource(draft_data_id=draft_data_id), has_version=has_version)
    monkeypatch.setattr(
        'roleplay_catalogue.routers.image_data.get_editable_resource',
        AsyncMock(return_value=database.resource.resource),
    )
    payload = ImageData(
        objectKey='key', contentType='image/png', byteSize=1,
        sha256='b' * 64, width=1, height=1,
    )
    with pytest.raises(HTTPException, match=detail) as excinfo:
        await create_image_data('image-id', payload, database, AUTHOR)
    assert excinfo.value.status_code == 409


async def test_published_image_data_requires_read_access_and_cannot_be_deleted(monkeypatch) -> None:
    document = image_document(published=True)
    database = ImageDatabase(image_resource(), [document])
    readable = AsyncMock(return_value=database.resource.resource)
    monkeypatch.setattr('roleplay_catalogue.routers.image_data.get_readable_resource', readable)
    monkeypatch.setattr(
        'roleplay_catalogue.routers.image_data.get_editable_resource',
        AsyncMock(return_value=database.resource.resource),
    )

    assert await get_image_data(document.id, database, None) == document
    readable.assert_awaited_once()
    with pytest.raises(HTTPException, match='immutable') as excinfo:
        await delete_image_data(document.id, database, AUTHOR)
    assert excinfo.value.status_code == 409


async def test_image_response_streams_content_and_honours_conditional_requests() -> None:
    document = image_document(published=True)
    version = ResourceVersion(
        id='version-id', resourceId='image-id', resourceType=ResourceType.IMAGE,
        versionNumber=1, dataId=document.id, metadata={'name': 'Image'}, publishedById=AUTHOR.id,
    )
    database = ImageDatabase(image_resource(), [document])
    database.resource_version.get_latest.return_value = version
    storage = SimpleNamespace(fetch=lambda _key: _stream_bytes(b'png'))

    normal = await image_response(
        database.resource.resource, database, storage, _request(), 'public, immutable',
    )
    assert normal.headers['etag'] == f'"{document.sha256}"'
    assert normal.headers['content-length'] == '3'
    assert b''.join([chunk async for chunk in normal.body_iterator]) == b'png'

    cached = await image_response(
        database.resource.resource, database, storage,
        _request((b'if-none-match', f'"other", "{document.sha256}"'.encode())),
        'public, immutable',
    )
    assert cached.status_code == 304
    assert 'content-length' not in cached.headers


async def _stream_bytes(payload):
    yield payload


def _request(*headers):
    return Request({'type': 'http', 'method': 'GET', 'path': '/', 'headers': list(headers)})


class AuthStub:
    def __init__(self, result=AUTHOR):
        self.result = result

    async def authenticate_api_key(self, _token):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def session_request(user_id=None):
    scope = {'type': 'http', 'method': 'GET', 'path': '/', 'headers': []}
    request = Request(scope)
    request.scope['session'] = {} if user_id is None else {'user_id': user_id}
    return request


async def test_authentication_dependencies_cover_session_and_bearer_paths() -> None:
    database = SimpleNamespace(user=SimpleNamespace(get=AsyncMock(return_value=AUTHOR)))
    bearer = SimpleNamespace(scheme='Bearer', credentials='secret')

    assert await authenticate_user(session_request('author-id'), database, AuthStub(), None) == AUTHOR
    assert await authenticate_user(session_request(), database, AuthStub(), bearer) == AUTHOR
    assert await authenticate_session_user(session_request('author-id'), database) == AUTHOR
    assert await optionally_authenticate_user(session_request(), database, AuthStub(), None) is None
    assert await authenticate_api_key(AuthStub(), bearer) == AUTHOR


async def test_authentication_dependencies_reject_missing_users_and_bad_keys() -> None:
    database = SimpleNamespace(user=SimpleNamespace(get=AsyncMock(return_value=None)))
    request = session_request('deleted-user')
    with pytest.raises(HTTPException) as excinfo:
        await authenticate_user(request, database, AuthStub(), None)
    assert excinfo.value.status_code == 401
    assert request.session == {}

    bad_key = SimpleNamespace(scheme='Bearer', credentials='bad')
    with pytest.raises(HTTPException) as excinfo:
        await optionally_authenticate_user(
            session_request(), database, AuthStub(UserCredentialMismatch('bad key')), bad_key,
        )
    assert excinfo.value.status_code == 401
    assert excinfo.value.headers == {'WWW-Authenticate': 'Bearer'}

    with pytest.raises(HTTPException, match='API key authentication required'):
        await authenticate_api_key(AuthStub(), None)


class WorldDataRepository(DataRepository):
    async def update(self, document):
        self.documents[document.id] = document
        return document


async def test_world_import_persists_metadata_media_and_updates_an_existing_draft(monkeypatch) -> None:
    from tests.unit_test.test_world_bundle import world_zip

    resource = Resource(
        id='world-id', resourceType=ResourceType.WORLD_SIMULATION_WORLD, authorId=AUTHOR.id,
        metadata={
            'name': 'Catalogue world', 'description': '', 'visibility': 'private',
            'tags': ['catalogue'],
        },
    )
    database = ImageDatabase(resource)
    database.world_data = WorldDataRepository()
    monkeypatch.setattr(
        'roleplay_catalogue.routers.worlds.get_editable_resource',
        AsyncMock(side_effect=lambda *_args: database.resource.resource),
    )
    imported_image = image_resource()
    create_image = AsyncMock(return_value=imported_image)
    monkeypatch.setattr('roleplay_catalogue.routers.worlds.create_image_resource', create_image)

    first = await import_world_bundle(
        resource.id, AUTHOR, database, SimpleNamespace(),
        UploadFile(filename='world.zip', file=__import__('io').BytesIO(world_zip()),
                   headers=Headers({'content-type': 'application/zip'})),
    )
    assert first.resource.metadata.description == ''
    assert first.resource.metadata.tags == ('catalogue', 'imported')
    assert first.resource.cover_image_resource_id == imported_image.id
    assert first.draft.data.media[0].image_resource_id == imported_image.id
    create_image.assert_awaited_once()

    database.resource.resource = first.resource
    second = await import_world_bundle(
        resource.id, AUTHOR, database, SimpleNamespace(),
        UploadFile(filename='world.zip', file=__import__('io').BytesIO(world_zip())),
    )
    assert second.draft.id == first.draft.id
    assert len(database.world_data.documents) == 1


async def test_world_import_translates_invalid_bundles_to_validation_errors(monkeypatch) -> None:
    resource = Resource(
        id='world-id', resourceType=ResourceType.WORLD_SIMULATION_WORLD,
        authorId=AUTHOR.id, metadata={'name': 'World'},
    )
    database = ImageDatabase(resource)
    database.world_data = WorldDataRepository()
    monkeypatch.setattr(
        'roleplay_catalogue.routers.worlds.get_editable_resource', AsyncMock(return_value=resource),
    )
    with pytest.raises(HTTPException, match='valid ZIP') as excinfo:
        await import_world_bundle(
            resource.id, AUTHOR, database, SimpleNamespace(),
            UploadFile(filename='bad.zip', file=__import__('io').BytesIO(b'not a zip')),
        )
    assert excinfo.value.status_code == 422


async def test_spa_static_files_serves_assets_and_falls_back_to_the_app_shell(tmp_path) -> None:
    (tmp_path / 'index.html').write_text('<main>app shell</main>')
    (tmp_path / 'asset.txt').write_text('asset')
    static = SPAStaticFiles(directory=tmp_path, html=True)
    scope = {'type': 'http', 'method': 'GET', 'path': '/', 'headers': []}

    asset = await static.get_response('asset.txt', scope)
    fallback = await static.get_response('client/route', scope)
    assert asset.path.endswith('asset.txt')
    assert fallback.path.endswith('index.html')


async def test_duplicate_key_errors_have_a_stable_public_response() -> None:
    response = await duplicate_key_error_handler(None, None)
    assert response.status_code == 409
    assert response.body == (
        b'{"detail":"A resource with the same identity or version already exists"}'
    )
