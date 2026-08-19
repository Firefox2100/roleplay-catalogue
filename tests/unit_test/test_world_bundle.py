import json
from io import BytesIO
from zipfile import ZipFile

import pytest

from roleplay_catalogue.models import (
    ImageDataDocument,
    Resource,
    ResourceMetadata,
    ResourceType,
    ResourceVersion,
    WorldBundleData,
    WorldMediaReference,
)
from roleplay_catalogue.components.world_bundle import (
    WorldBundleError,
    apply_resource_metadata_to_world,
    build_world_bundle,
    parse_world_bundle,
    resource_language_from_world,
)


def world_zip(*, spec_version: str = '1.0', duplicate_id: bool = False) -> bytes:
    output = BytesIO()
    world_id = 'world-1'
    with ZipFile(output, 'w') as archive:
        archive.writestr('manifest.json', json.dumps({
            'spec': 'wse_world', 'spec_version': spec_version,
        }))
        archive.writestr('world.json', json.dumps({
            'id': world_id, 'name': 'Test world', 'starting_time': '2026-01-01T00:00:00Z',
            'language': 'en', 'cover_media_id': 'cover-1', 'metadata': {'tags': ['imported']},
        }))
        archive.writestr('author.json', 'null')
        archive.writestr('data/locations.jsonl', json.dumps({
            'id': world_id if duplicate_id else 'location-1', 'name': 'Town',
        }) + '\n')
        archive.writestr('data/characters.jsonl', json.dumps({
            'id': 'character-1', 'name': 'Ari', 'location_id': 'location-1',
        }) + '\n')
        archive.writestr('media/manifest.jsonl', json.dumps({
            'id': 'cover-1', 'type': 'image/png', 'file': 'media/cover.png',
        }) + '\n')
        archive.writestr('media/cover.png', b'not-decoded-by-the-bundle-parser')
    return output.getvalue()


def test_world_bundle_import_preserves_graph_and_image_files() -> None:
    parsed = parse_world_bundle(world_zip())

    assert parsed.data.world['name'] == 'Test world'
    assert parsed.data.sections['locations'][0]['id'] == 'location-1'
    assert parsed.data.sections['characters'][0]['location_id'] == 'location-1'
    assert parsed.data.media[0].media_id == 'cover-1'
    assert parsed.image_files['cover-1'] == b'not-decoded-by-the-bundle-parser'


def test_world_bundle_rejects_unsupported_version() -> None:
    with pytest.raises(WorldBundleError, match='v1.0'):
        parse_world_bundle(world_zip(spec_version='2.0'))


def test_world_bundle_rejects_duplicate_graph_ids() -> None:
    with pytest.raises(WorldBundleError, match='Duplicate graph id'):
        parse_world_bundle(world_zip(duplicate_id=True))


def test_catalogue_metadata_controls_exported_world_language_and_description() -> None:
    data = parse_world_bundle(world_zip()).data
    resource = Resource(
        resourceType=ResourceType.WORLD_SIMULATION_WORLD,
        authorId='author',
        metadata=ResourceMetadata(
            name='目录世界', description='目录描述', language='zh-cn', tags=('catalogue',),
        ),
    )

    updated = apply_resource_metadata_to_world(data, resource)

    assert updated.world['name'] == '目录世界'
    assert updated.world['description'] == '目录描述'
    assert updated.world['language'] == 'zh'
    assert updated.world['metadata']['tags'] == ['catalogue']
    assert resource_language_from_world('zh').value == 'zh-cn'
    assert resource_language_from_world('en').value == 'en-uk'


class VersionRepo:
    def __init__(self, versions=()):
        self.versions = {version.resource_id: version for version in versions}

    async def get_latest(self, resource_id):
        return self.versions.get(resource_id)


class ImageDataRepo:
    def __init__(self, documents=()):
        self.documents = {document.id: document for document in documents}

    async def get(self, data_id):
        return self.documents.get(data_id)


class FakeDatabase:
    def __init__(self, *, versions=(), image_documents=()):
        self.resource_version = VersionRepo(versions)
        self.image_data = ImageDataRepo(image_documents)


class FakeStorage:
    def __init__(self, objects):
        self.objects = objects

    async def fetch(self, key):
        yield self.objects[key]


async def test_build_world_bundle_embeds_resolvable_media_files() -> None:
    image_version = ResourceVersion(
        resourceId='cover-resource', resourceType=ResourceType.IMAGE, versionNumber=1,
        dataId='cover-data', metadata={'name': 'Cover'}, publishedById='author',
    )
    document = ImageDataDocument(
        id='cover-data', resourceId='cover-resource', objectKey='images/cover.png',
        contentType='image/png', byteSize=3, sha256='b' * 64, width=1, height=1,
    )
    database = FakeDatabase(versions=[image_version], image_documents=[document])
    storage = FakeStorage({'images/cover.png': b'png-bytes'})
    data = WorldBundleData(
        world={
            'id': 'world-1', 'name': 'Test world',
            'starting_time': '2026-01-01T00:00:00Z', 'language': 'en',
        },
        media=[WorldMediaReference(
            mediaId='cover-1', imageResourceId='cover-resource', record={'id': 'cover-1'},
        )],
    )

    archive_bytes = await build_world_bundle(data, database, storage)

    with ZipFile(BytesIO(archive_bytes)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['world_id'] == 'world-1'
        assert manifest['world_name'] == 'Test world'
        world = json.loads(archive.read('world.json'))
        assert world['name'] == 'Test world'
        media_row = json.loads(archive.read('media/manifest.jsonl').decode().strip())
        assert media_row['id'] == 'cover-1'
        assert media_row['hash'] == 'b' * 64
        assert media_row['type'] == 'image/png'
        assert archive.read(media_row['file']) == b'png-bytes'


async def test_build_world_bundle_leaves_unresolvable_media_rows_untouched() -> None:
    database = FakeDatabase()
    storage = FakeStorage({})
    data = WorldBundleData(
        world={
            'id': 'world-1', 'name': 'Test world',
            'starting_time': '2026-01-01T00:00:00Z', 'language': 'en',
        },
        media=[WorldMediaReference(
            mediaId='missing-1', imageResourceId='missing-resource',
            record={'id': 'missing-1', 'type': 'image/png', 'file': 'media/missing.png'},
        )],
    )

    archive_bytes = await build_world_bundle(data, database, storage)

    with ZipFile(BytesIO(archive_bytes)) as archive:
        media_row = json.loads(archive.read('media/manifest.jsonl').decode().strip())
        assert media_row == {'id': 'missing-1', 'type': 'image/png', 'file': 'media/missing.png'}
        assert 'media/missing.png' not in archive.namelist()
