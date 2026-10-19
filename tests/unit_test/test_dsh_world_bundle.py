from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from roleplay_catalogue.components import DshWorldBundleError, parse_dsh_world_bundle


def world_zip(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return output.getvalue()


def test_indexes_and_normalizes_native_world_folder():
    payload = world_zip({
        'harbour/world.json': json.dumps({
            'id': 'harbour', 'name': 'Grey Harbour', 'version': '1.2',
            'author': {'name': 'Alice'},
        }).encode(),
        'harbour/characters/mira/character.json': b'{"name":"Mira"}',
        'harbour/prompts/en/roleplay/style.md': b'Keep it windswept.',
    })

    parsed = parse_dsh_world_bundle(payload, 'drafts/world.zip')
    data = parsed.data

    assert data.world_id == 'harbour'
    assert data.world_name == 'Grey Harbour'
    assert data.world_version == '1.2'
    assert data.author_name == 'Alice'
    assert data.folder_name == 'harbour'
    assert data.byte_size == len(parsed.payload)
    assert [item.path for item in data.files] == [
        'harbour/characters/mira/character.json',
        'harbour/prompts/en/roleplay/style.md',
        'harbour/world.json',
    ]


@pytest.mark.parametrize('files,message', [
    ({'readme.txt': b'hello'}, 'one top-level world folder'),
    ({'a/world.json': b'{"name":"A"}', 'b/file.txt': b'x'}, 'same top-level world folder'),
    ({'bad/world.json': b'[]'}, 'must contain an object'),
    ({'bad/world.json': b'{"name":""}'}, 'non-empty name'),
    ({'../world.json': b'{"name":"Bad"}'}, 'Unsafe archive path'),
])
def test_rejects_invalid_or_unsafe_world_archives(files, message):
    with pytest.raises(DshWorldBundleError, match=message):
        parse_dsh_world_bundle(world_zip(files), 'drafts/world.zip')


def test_assigns_a_stable_id_and_returns_a_normalized_install_ready_zip():
    parsed = parse_dsh_world_bundle(world_zip({
        'harbour/world.json': b'{"name":"Harbour"}',
    }), 'drafts/world.zip')

    assert parsed.data.world_id
    with ZipFile(BytesIO(parsed.payload)) as archive:
        world = json.loads(archive.read('harbour/world.json'))
    assert world['id'] == parsed.data.world_id


def test_rejects_windows_traversal_paths():
    with pytest.raises(DshWorldBundleError, match='Unsafe archive path'):
        parse_dsh_world_bundle(world_zip({
            'harbour/world.json': b'{"name":"Harbour"}',
            'harbour\\..\\outside.txt': b'bad',
        }), 'drafts/world.zip')


def test_fork_normalization_assigns_a_new_world_identity():
    source = world_zip({'harbour/world.json': b'{"id":"original","name":"Harbour"}'})

    parsed = parse_dsh_world_bundle(
        source, 'drafts/fork.zip', assign_new_id=True,
    )

    assert parsed.data.world_id != 'original'
    with ZipFile(BytesIO(parsed.payload)) as archive:
        assert json.loads(archive.read('harbour/world.json'))['id'] == parsed.data.world_id
