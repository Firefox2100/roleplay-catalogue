from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from roleplay_catalogue.misc import ResourceVisibility
from roleplay_catalogue.models import User
from roleplay_catalogue.components.image_ingestion import create_image_resource


AUTHOR = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')
OTHER_AUTHOR = User(id='other-id', username='other', email='other@example.com', passwordHash='hash')


def png_bytes(color: str = 'red') -> bytes:
    buffer = BytesIO()
    Image.new('RGB', (4, 4), color).save(buffer, format='PNG')
    return buffer.getvalue()


class ImageDataRepo:
    def __init__(self):
        self.documents = {}

    async def list_by_sha256(self, digest):
        return [document for document in self.documents.values() if document.sha256 == digest]

    async def create(self, document):
        self.documents[document.id] = document
        return document


class ResourceRepo:
    def __init__(self):
        self.documents = {}

    async def create(self, resource):
        self.documents[resource.id] = resource
        return resource

    async def get(self, resource_id):
        return self.documents.get(resource_id)


class VersionRepo:
    def __init__(self):
        self.documents = {}

    async def create(self, version):
        self.documents[version.id] = version
        return version


class FakeDatabase:
    def __init__(self, *, fail_transaction: bool = False):
        self.image_data = ImageDataRepo()
        self.resource = ResourceRepo()
        self.resource_version = VersionRepo()
        self._fail_transaction = fail_transaction

    async def transaction(self, operation):
        if self._fail_transaction:
            raise RuntimeError('transaction failed')
        return await operation()


class FakeStorage:
    def __init__(self):
        self.uploaded: dict[str, bytes] = {}
        self.removed: list[str] = []

    async def upload(self, key, data, content_type):
        self.uploaded[key] = data

    async def wait_until_available(self, key):
        assert key in self.uploaded

    async def remove(self, key):
        self.removed.append(key)
        self.uploaded.pop(key, None)


async def test_blank_name_is_rejected() -> None:
    with pytest.raises(HTTPException) as excinfo:
        await create_image_resource(
            name='   ', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
            source=png_bytes(), user=AUTHOR, database=FakeDatabase(), storage=FakeStorage(),
        )
    assert excinfo.value.status_code == 422


async def test_creates_a_private_by_default_resource_and_uploads_once() -> None:
    database = FakeDatabase()
    storage = FakeStorage()

    resource = await create_image_resource(
        name=' Cover Art ', description=' Desc ', visibility=ResourceVisibility.PRIVATE,
        tags=[' tag ', ''], source=png_bytes(), user=AUTHOR, database=database, storage=storage,
    )

    assert resource.metadata.name == 'Cover Art'
    assert resource.metadata.description == 'Desc'
    assert resource.metadata.tags == ('tag',)
    assert resource.author_id == AUTHOR.id
    assert resource.id in database.resource.documents
    assert len(database.resource_version.documents) == 1
    assert len(storage.uploaded) == 1


async def test_reuploading_identical_bytes_by_the_same_author_reuses_the_resource() -> None:
    database = FakeDatabase()
    storage = FakeStorage()
    data = png_bytes()

    first = await create_image_resource(
        name='First', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
        source=data, user=AUTHOR, database=database, storage=storage,
    )
    second = await create_image_resource(
        name='First again', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
        source=data, user=AUTHOR, database=database, storage=storage,
    )

    assert second.id == first.id
    assert len(database.resource.documents) == 1
    assert len(storage.uploaded) == 1


async def test_reuploading_identical_bytes_by_a_different_author_creates_a_new_resource() -> None:
    database = FakeDatabase()
    storage = FakeStorage()
    data = png_bytes()

    first = await create_image_resource(
        name='First', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
        source=data, user=AUTHOR, database=database, storage=storage,
    )
    second = await create_image_resource(
        name='Second', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
        source=data, user=OTHER_AUTHOR, database=database, storage=storage,
    )

    assert second.id != first.id
    assert second.author_id == OTHER_AUTHOR.id
    assert len(database.resource.documents) == 2


async def test_storage_object_is_removed_when_persisting_fails_after_upload() -> None:
    database = FakeDatabase(fail_transaction=True)
    storage = FakeStorage()

    with pytest.raises(RuntimeError):
        await create_image_resource(
            name='Cover', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
            source=png_bytes(), user=AUTHOR, database=database, storage=storage,
        )

    assert not storage.uploaded
    assert len(storage.removed) == 1
    assert not database.resource.documents


async def test_invalid_image_bytes_are_rejected() -> None:
    with pytest.raises(HTTPException) as excinfo:
        await create_image_resource(
            name='Cover', description='', visibility=ResourceVisibility.PRIVATE, tags=[],
            source=b'not an image', user=AUTHOR, database=FakeDatabase(), storage=FakeStorage(),
        )
    assert excinfo.value.status_code == 422
