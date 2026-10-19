"""Safe normalization and inspection of DeepSeek Harness world folder ZIPs."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
import stat
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from roleplay_catalogue.models import DshWorldData, DshWorldFile


class DshWorldBundleError(ValueError):
    """Raised when an uploaded ZIP cannot be used as a native world folder."""


@dataclass(frozen=True)
class ParsedDshWorldBundle:
    """Normalized package, its catalogue index, and optional native cover bytes."""

    payload: bytes
    data: DshWorldData
    cover: bytes | None = None


def _safe_path(name: str) -> PurePosixPath:
    if '\\' in name or '\x00' in name:
        raise DshWorldBundleError(f'Unsafe archive path: {name}')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise DshWorldBundleError(f'Unsafe archive path: {name}')
    if any(part in ('', '.') for part in path.parts):
        raise DshWorldBundleError(f'Ambiguous archive path: {name}')
    return path


def _read_json(content: bytes, path: str):
    try:
        return json.loads(content.decode('utf-8-sig'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DshWorldBundleError(f'{path} must be valid UTF-8 JSON') from error


def _validate_documents(contents: dict[str, bytes]) -> None:
    """Catch malformed native documents without duplicating the Harness domain model."""
    for path, content in contents.items():
        if path.endswith('.json'):
            _read_json(content, path)
        elif path.endswith('.jsonl'):
            try:
                lines = content.decode('utf-8-sig').splitlines()
            except UnicodeDecodeError as error:
                raise DshWorldBundleError(f'{path} must be valid UTF-8 JSON lines') from error
            for line_number, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as error:
                    raise DshWorldBundleError(
                        f'{path}:{line_number} must be valid JSON'
                    ) from error


def _cover_bytes(contents: dict[str, bytes], root: str, world: dict) -> bytes | None:
    media_id = world.get('cover_media_id')
    if not isinstance(media_id, str) or not media_id:
        return None
    manifest_path = f'{root}/media/manifest.jsonl'
    manifest = contents.get(manifest_path)
    if manifest is None:
        raise DshWorldBundleError('world.json names a cover but media/manifest.jsonl is missing')
    for line in manifest.decode('utf-8-sig').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get('id') == media_id:
            file_name = row.get('file')
            if not isinstance(file_name, str) or not file_name:
                raise DshWorldBundleError(f'Media {media_id!r} has no file')
            cover_path = _safe_path(f'{root}/{file_name}').as_posix()
            suffix = PurePosixPath(cover_path).suffix.casefold()
            if suffix not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'):
                raise DshWorldBundleError('World cover must use a supported raster image format')
            if cover_path not in contents:
                raise DshWorldBundleError(f'World cover file is missing: {file_name}')
            return contents[cover_path]
    raise DshWorldBundleError(f'Cover media {media_id!r} is missing from media/manifest.jsonl')


def parse_dsh_world_bundle(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        payload: bytes, object_key: str, *, assign_new_id: bool = False,
) -> ParsedDshWorldBundle:
    """Normalize, safely validate, and index an agentic-roleplay world-folder ZIP."""
    try:
        archive = ZipFile(BytesIO(payload))
    except BadZipFile as error:
        raise DshWorldBundleError('File is not a valid ZIP archive') from error

    contents: dict[str, bytes] = {}
    folded_names: set[str] = set()
    expanded_size = 0
    with archive:
        infos = archive.infolist()
        if len(infos) > 5_000:
            raise DshWorldBundleError('World archive contains too many files')
        for info in infos:
            path = _safe_path(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise DshWorldBundleError(f'Symbolic links are not allowed: {info.filename}')
            if info.flag_bits & 0x1:
                raise DshWorldBundleError('Encrypted ZIP entries are not supported')
            if info.is_dir():
                continue
            canonical = path.as_posix()
            folded = canonical.casefold()
            if canonical in contents or folded in folded_names:
                raise DshWorldBundleError(f'Duplicate or case-colliding archive path: {canonical}')
            expanded_size += info.file_size
            if expanded_size > 512 * 1024 * 1024:
                raise DshWorldBundleError('Expanded world folder is too large')
            contents[canonical] = archive.read(info)
            folded_names.add(folded)

    candidates = [path for path in contents if PurePosixPath(path).name == 'world.json']
    if len(candidates) != 1 or len(PurePosixPath(candidates[0]).parts) != 2:
        raise DshWorldBundleError('ZIP must contain one top-level world folder with world.json')
    world_path = PurePosixPath(candidates[0])
    root = world_path.parts[0]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', root):
        raise DshWorldBundleError('Top-level world folder has an unsafe or unsupported name')
    if any(PurePosixPath(path).parts[0] != root for path in contents):
        raise DshWorldBundleError('All files must be inside the same top-level world folder')

    _validate_documents(contents)
    world = _read_json(contents[world_path.as_posix()], world_path.as_posix())
    if not isinstance(world, dict):
        raise DshWorldBundleError('world.json must contain an object')
    name = world.get('name')
    if not isinstance(name, str) or not name.strip():
        raise DshWorldBundleError('world.json must contain a non-empty name')
    world_id = world.get('id')
    if world_id is not None and (not isinstance(world_id, str) or not world_id.strip()):
        raise DshWorldBundleError('world.json id must be a non-empty string when present')
    if world_id is None or assign_new_id:
        world_id = str(uuid4())
        world = {**world, 'id': world_id}
        contents[world_path.as_posix()] = (
            json.dumps(world, ensure_ascii=False, indent=2) + '\n'
        ).encode('utf-8')

    metadata = world.get('metadata')
    tags = metadata.get('tags', []) if isinstance(metadata, dict) else []
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise DshWorldBundleError('world.json metadata.tags must be a list of strings')
    description = world.get('description', '')
    if not isinstance(description, str):
        raise DshWorldBundleError('world.json description must be text')
    author = world.get('author')
    author_name = author.get('name') if isinstance(author, dict) else None
    version = world.get('version')
    cover = _cover_bytes(contents, root, world)

    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as normalized:
        for path in sorted(contents):
            normalized.writestr(path, contents[path])
    normalized_payload = output.getvalue()
    files = tuple(DshWorldFile(
        path=path, byteSize=len(content), sha256=sha256(content).hexdigest(),
    ) for path, content in sorted(contents.items()))
    data = DshWorldData(
        worldId=world_id.strip(), worldName=name.strip(),
        worldVersion=str(version).strip() if version is not None else None,
        authorName=(author_name.strip() if isinstance(author_name, str) and author_name.strip()
                    else None),
        description=description.strip(), tags=tuple(tag.strip() for tag in tags if tag.strip()),
        folderName=root, objectKey=object_key, byteSize=len(normalized_payload),
        sha256=sha256(normalized_payload).hexdigest(), files=files,
    )
    return ParsedDshWorldBundle(payload=normalized_payload, data=data, cover=cover)
