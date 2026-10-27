"""Focused tests for atomic DeepSeek Harness world ZIP ingestion."""

from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zipfile import ZipFile

from fastapi import HTTPException, UploadFile
import pytest

from roleplay_catalogue.components.dsh_world_bundle import ParsedDshWorldBundle
from roleplay_catalogue.models import DshWorldDataDocument, Resource, ResourceType, User
import roleplay_catalogue.routers.dsh_worlds as router


USER = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')


def world_zip(name: str = 'Harbour') -> bytes:
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.writestr('harbour/world.json', json.dumps({'name': name}))
    return output.getvalue()


def resource(draft_data_id: str | None = None) -> Resource:
    return Resource(
        id='world-id', resourceType=ResourceType.DSH_AGENTIC_ROLEPLAY_WORLD,
        authorId=USER.id, draftDataId=draft_data_id,
        metadata={'name': 'Harbour', 'visibility': 'private', 'tags': ['sea']},
    )


def upload(payload: bytes) -> UploadFile:
    return UploadFile(filename='world.zip', file=BytesIO(payload))


class DataRepository:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = None
        self.updated = None

    async def get(self, _document_id):
        return self.existing

    async def create(self, document):
        self.created = document

    async def update(self, document):
        self.updated = document


class ResourceRepository:
    def __init__(self, item, *, disappear=False):
        self.item = item
        self.disappear = disappear

    async def apply_update(self, _resource_id, fields):
        if self.disappear:
            return None
        return self.item.model_copy(update={
            'draft_data_id': fields['draftDataId'],
            'cover_image_resource_id': fields['coverImageResourceId'],
        })


class Database:
    def __init__(self, item, existing=None, *, disappear=False):
        self.dsh_world_data = DataRepository(existing)
        self.resource = ResourceRepository(item, disappear=disappear)

    async def transaction(self, operation):
        return await operation()


class Storage:
    def __init__(self, *, fail_wait=False):
        self.uploads = []
        self.removed = []
        self.fail_wait = fail_wait

    async def upload(self, key, payload, content_type):
        self.uploads.append((key, payload, content_type))

    async def wait_until_available(self, _key):
        if self.fail_wait:
            raise RuntimeError('storage unavailable')

    async def remove(self, key):
        self.removed.append(key)


@pytest.fixture
def configure(monkeypatch):
    monkeypatch.setattr(router, 'CONFIG', SimpleNamespace(dsh_world_max_bytes=1024 * 1024))

    def apply(item):
        monkeypatch.setattr(
            router, 'get_editable_resource', AsyncMock(return_value=item),
        )

    return apply


@pytest.mark.asyncio
async def test_import_creates_a_normalized_draft(configure):
    item = resource()
    configure(item)
    database = Database(item)
    storage = Storage()

    response = await router.import_dsh_world(
        item.id, USER, database, storage, upload(world_zip()),
    )

    assert response.resource.draft_data_id == response.draft.id
    assert response.draft.data.world_name == 'Harbour'
    assert database.dsh_world_data.created == response.draft
    key, payload, content_type = storage.uploads[0]
    assert key == response.draft.data.object_key
    assert payload != b''
    assert content_type == 'application/zip'


@pytest.mark.asyncio
async def test_import_replaces_existing_draft_and_removes_old_archive(configure):
    parsed = router.parse_dsh_world_bundle(world_zip('Old Harbour'), 'drafts/old.zip')
    existing = DshWorldDataDocument(resourceId='world-id', data=parsed.data)
    item = resource(existing.id)
    configure(item)
    database = Database(item, existing)
    storage = Storage()

    response = await router.import_dsh_world(
        item.id, USER, database, storage, upload(world_zip('New Harbour')),
    )

    assert response.draft.id == existing.id
    assert response.draft.data.world_name == 'New Harbour'
    assert database.dsh_world_data.updated == response.draft
    assert storage.removed == ['drafts/old.zip']


@pytest.mark.asyncio
async def test_import_uses_native_cover_for_the_resource(configure, monkeypatch):
    item = resource()
    configure(item)
    parsed = router.parse_dsh_world_bundle(world_zip(), 'drafts/cover.zip')
    monkeypatch.setattr(router, 'parse_dsh_world_bundle', lambda *_: ParsedDshWorldBundle(
        payload=parsed.payload, data=parsed.data, cover=b'cover-bytes',
    ))
    create_cover = AsyncMock(return_value=SimpleNamespace(id='cover-id'))
    monkeypatch.setattr(router, 'create_image_resource', create_cover)

    response = await router.import_dsh_world(
        item.id, USER, Database(item), Storage(), upload(world_zip()),
    )

    assert response.resource.cover_image_resource_id == 'cover-id'
    create_cover.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_rejects_oversized_and_invalid_archives(configure, monkeypatch):
    item = resource()
    configure(item)
    monkeypatch.setattr(router, 'CONFIG', SimpleNamespace(dsh_world_max_bytes=3))

    with pytest.raises(HTTPException) as oversized:
        await router.import_dsh_world(item.id, USER, Database(item), Storage(), upload(b'1234'))
    assert oversized.value.status_code == 413

    monkeypatch.setattr(router, 'CONFIG', SimpleNamespace(dsh_world_max_bytes=1024))
    with pytest.raises(HTTPException) as invalid:
        await router.import_dsh_world(item.id, USER, Database(item), Storage(), upload(b'bad'))
    assert invalid.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize('fail_wait,disappear', [(True, False), (False, True)])
async def test_import_removes_new_archive_when_persistence_fails(
        configure, fail_wait, disappear,
):
    item = resource()
    configure(item)
    database = Database(item, disappear=disappear)
    storage = Storage(fail_wait=fail_wait)

    with pytest.raises(RuntimeError):
        await router.import_dsh_world(
            item.id, USER, database, storage, upload(world_zip()),
        )

    assert storage.removed == [storage.uploads[0][0]]
