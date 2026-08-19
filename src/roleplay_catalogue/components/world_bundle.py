import json
from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from roleplay_catalogue.models import ResourceLanguage, WorldBundleData, WorldMediaReference
from roleplay_catalogue.models.roleplay_resource.world import (
    WORLD_BUNDLE_SPEC,
    WORLD_BUNDLE_SPEC_VERSION,
    WORLD_CONFIG_NAMES,
    WORLD_SECTION_NAMES,
)


class WorldBundleError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedWorldBundle:
    data: WorldBundleData
    image_files: dict[str, bytes]


def apply_resource_metadata_to_world(data: WorldBundleData, resource) -> WorldBundleData:
    """Translate catalogue metadata into the World Engine's v1.0 vocabulary."""
    language = {'en-uk': 'en', 'zh-cn': 'zh'}[resource.metadata.language.value]
    world_metadata = {**(data.world.get('metadata') or {}), 'tags': list(resource.metadata.tags)}
    return data.model_copy(update={'world': {
        **data.world,
        'name': resource.metadata.name,
        'description': resource.metadata.description or None,
        'language': language,
        'metadata': world_metadata,
    }})


def resource_language_from_world(language: str) -> ResourceLanguage:
    return {
        'en': ResourceLanguage.ENGLISH_UK,
        'zh': ResourceLanguage.CHINESE_SIMPLIFIED,
    }[language]


def _read_json(archive: ZipFile, name: str, required: bool = True):
    try:
        payload = archive.read(name)
    except KeyError:
        if not required:
            return None
        raise WorldBundleError(f'World bundle is missing {name}') from None
    try:
        return json.loads(payload.decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorldBundleError(f'{name} is not valid UTF-8 JSON') from error


def _read_jsonl(archive: ZipFile, name: str) -> list[dict]:
    if name not in archive.namelist():
        return []
    try:
        text = archive.read(name).decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise WorldBundleError(f'{name} is not valid UTF-8 JSONL') from error
    rows = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise WorldBundleError(f'{name} has invalid JSON on line {line_number}') from error
        if not isinstance(row, dict):
            raise WorldBundleError(f'{name} line {line_number} is not an object')
        rows.append(row)
    return rows


def parse_world_bundle(payload: bytes, *, max_files: int = 2_000,
                       max_uncompressed_bytes: int = 250 * 1024 * 1024) -> ParsedWorldBundle:
    try:
        archive = ZipFile(BytesIO(payload))
    except BadZipFile as error:
        raise WorldBundleError('Uploaded file is not a valid ZIP archive') from error
    with archive:
        members = archive.infolist()
        if len(members) > max_files:
            raise WorldBundleError('World bundle contains too many files')
        if sum(member.file_size for member in members) > max_uncompressed_bytes:
            raise WorldBundleError('World bundle expands beyond the permitted size')
        if any(member.filename.startswith('/') or '..' in member.filename.split('/')
               for member in members):
            raise WorldBundleError('World bundle contains an unsafe file path')
        if archive.testzip() is not None:
            raise WorldBundleError('World bundle is corrupted')

        manifest = _read_json(archive, 'manifest.json')
        if not isinstance(manifest, dict) or manifest.get('spec') != WORLD_BUNDLE_SPEC or \
                manifest.get('spec_version') != WORLD_BUNDLE_SPEC_VERSION:
            raise WorldBundleError('Only World Simulation Engine world bundle v1.0 is supported')
        world = _read_json(archive, 'world.json')
        if not isinstance(world, dict):
            raise WorldBundleError('world.json must contain an object')
        author = _read_json(archive, 'author.json', required=False)
        if author is not None and not isinstance(author, dict):
            raise WorldBundleError('author.json must contain an object or null')

        sections = {
            name: _read_jsonl(archive, f'data/{name}.jsonl')
            for name in WORLD_SECTION_NAMES
        }
        configs = {
            name: _read_jsonl(archive, f'configs/{name}.jsonl')
            for name in WORLD_CONFIG_NAMES
        }
        prompts = _read_jsonl(archive, 'prompts.jsonl')
        workflows = _read_jsonl(archive, 'workflows.jsonl')
        media_rows = _read_jsonl(archive, 'media/manifest.jsonl')
        media = []
        image_files = {}
        for row in media_rows:
            media_id = row.get('id')
            if not media_id:
                raise WorldBundleError('A media manifest entry is missing its id')
            media.append(WorldMediaReference(mediaId=media_id, record=row))
            file_name = row.get('file')
            if row.get('type') == 'image/png' and file_name in archive.namelist():
                image_files[media_id] = archive.read(file_name)

        try:
            data = WorldBundleData(
                spec=manifest['spec'], specVersion=manifest['spec_version'],
                world=world, author=author, sections=sections, configs=configs,
                prompts=prompts, workflows=workflows, media=media,
            )
        except ValueError as error:
            raise WorldBundleError(f'World bundle data is invalid: {error}') from error
        return ParsedWorldBundle(data=data, image_files=image_files)


async def build_world_bundle(data: WorldBundleData, database, storage) -> bytes:
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps({
            'spec': WORLD_BUNDLE_SPEC,
            'spec_version': WORLD_BUNDLE_SPEC_VERSION,
            'world_id': data.world.get('id'),
            'world_name': data.world.get('name'),
        }, ensure_ascii=False, indent=2))
        archive.writestr('world.json', json.dumps(data.world, ensure_ascii=False, indent=2))
        archive.writestr('author.json', json.dumps(data.author, ensure_ascii=False, indent=2))
        for name in WORLD_SECTION_NAMES:
            archive.writestr(f'data/{name}.jsonl', _jsonl(data.sections.get(name, [])))
        for name in WORLD_CONFIG_NAMES:
            archive.writestr(f'configs/{name}.jsonl', _jsonl(data.configs.get(name, [])))
        archive.writestr('prompts.jsonl', _jsonl(data.prompts))
        archive.writestr('workflows.jsonl', _jsonl(data.workflows))

        media_rows = []
        for media in data.media:
            row = dict(media.record)
            if media.image_resource_id:
                version = await database.resource_version.get_latest(media.image_resource_id)
                document = await database.image_data.get(version.data_id) if version else None
                if document:
                    file_name = row.get('file') or f'media/files/{media.media_id}.png'
                    row.update({
                        'id': media.media_id,
                        'type': 'image/png',
                        'hash': document.sha256,
                        'file': file_name,
                    })
                    content = b''.join([chunk async for chunk in storage.fetch(document.object_key)])
                    archive.writestr(file_name, content)
            media_rows.append(row)
        archive.writestr('media/manifest.jsonl', _jsonl(media_rows))
    return output.getvalue()


def _jsonl(rows: list[dict]) -> bytes:
    text = '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)
    return (text + ('\n' if text else '')).encode('utf-8')
