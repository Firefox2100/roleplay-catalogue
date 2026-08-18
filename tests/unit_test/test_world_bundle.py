import json
from io import BytesIO
from zipfile import ZipFile

import pytest

from roleplay_catalogue.services.world_bundle import WorldBundleError, parse_world_bundle


def world_zip(*, spec_version: str = '1.0', duplicate_id: bool = False) -> bytes:
    output = BytesIO()
    world_id = 'world-1'
    with ZipFile(output, 'w') as archive:
        archive.writestr('manifest.json', json.dumps({
            'spec': 'wse_world', 'spec_version': spec_version,
        }))
        archive.writestr('world.json', json.dumps({
            'id': world_id, 'name': 'Test world', 'starting_time': '2026-01-01T00:00:00Z',
            'language': 'en', 'cover_media_id': 'cover-1',
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
