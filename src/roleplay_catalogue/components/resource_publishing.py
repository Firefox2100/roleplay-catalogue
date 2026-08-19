from asyncio import to_thread
from base64 import b64encode
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from PIL import Image, PngImagePlugin

from roleplay_catalogue.models import (
    LorebookReference,
    Resource,
    ResourceType,
    ResourceVersion,
    ResourceVisibility,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern import SillyTavernCardV3
from roleplay_catalogue.models.roleplay_resource.silly_tavern.card_v3 import (
    SillyTavernCardV3Data,
)
from roleplay_catalogue.services import DatabaseService, StorageService

from .content_diff import build_content_diff, render_release_text
from .resource_access import resource_editor_ids


async def read_storage_object(storage: StorageService, key: str) -> bytes:
    return b''.join([chunk async for chunk in storage.fetch(key)])


def package_card_as_png(cover: bytes, card_json: bytes) -> bytes:
    with Image.open(BytesIO(cover)) as opened:
        opened.load()
        image = opened.convert('RGBA' if opened.mode in ('RGBA', 'LA') else 'RGB')
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('ccv3', b64encode(card_json).decode('ascii'))
        output = BytesIO()
        image.save(output, format='PNG', pnginfo=metadata, optimize=True)
        return output.getvalue()


async def build_character_artifact(*, database: DatabaseService,
                                   storage: StorageService,
                                   card: SillyTavernCardV3,
                                   cover_image_resource_id: str | None,
                                   ) -> tuple[bytes, str, str]:
    card_json = card.model_dump_json(exclude_none=True).encode('utf-8')
    if not cover_image_resource_id:
        return card_json, 'application/json', '.json'
    image_version = await database.resource_version.get_latest(cover_image_resource_id)
    image_document = await database.image_data.get(image_version.data_id) if image_version else None
    if not image_document:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Cover image content is missing')
    cover = await read_storage_object(storage, image_document.object_key)
    return await to_thread(package_card_as_png, cover, card_json), 'image/png', '.png'


async def merge_linked_lorebooks(character: SillyTavernCardV3Data,
                                 links: tuple[LorebookReference, ...],
                                 database: DatabaseService,
                                 *, character_author_name: str,
                                 character_editor_ids: frozenset[str],
                                 require_releases: bool = False,
                                 required_visibility: ResourceVisibility | None = None,
                                 ) -> SillyTavernCardV3Data:
    """Embed linked books in selection order, retaining private-book settings as the base."""
    books = []
    authors = [character_author_name] if character.character_book else []
    for link in links:
        resource = await database.resource.get(link.resource_id)
        if not resource or resource.resource_type != ResourceType.SILLY_TAVERN_LOREBOOK:
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook no longer exists')
        if require_releases and link.version_id is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                'Character releases cannot link lorebook drafts; select a lorebook release first',
            )
        version = await database.resource_version.get(link.version_id) if link.version_id else None
        if version and (version.resource_id != resource.id or
                        version.resource_type != ResourceType.SILLY_TAVERN_LOREBOOK):
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook release is invalid')
        if version and version.visibility == ResourceVisibility.PRIVATE and \
                not (resource_editor_ids(resource) & character_editor_ids):
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook release is no longer readable')
        if version and required_visibility:
            permitted = {
                ResourceVisibility.PRIVATE: set(ResourceVisibility),
                ResourceVisibility.AUTHENTICATED: {
                    ResourceVisibility.AUTHENTICATED, ResourceVisibility.PUBLIC,
                },
                ResourceVisibility.PUBLIC: {ResourceVisibility.PUBLIC},
            }[required_visibility]
            if version.visibility not in permitted:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    'A linked lorebook release is less visible than the character release',
                )
        if link.version_id is None and not (resource_editor_ids(resource) & character_editor_ids):
            raise HTTPException(status.HTTP_409_CONFLICT, 'Only editable lorebook drafts may be linked')
        document = None
        if link.version_id is None and resource.draft_data_id:
            document = await database.silly_tavern_lorebook_data.get(resource.draft_data_id)
        elif version:
            document = (
                await database.silly_tavern_lorebook_data.get(version.data_id)
            )
        if not document:
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook has no selected content')
        books.append(document.data)
        lorebook_author = await database.user.get(resource.author_id)
        if lorebook_author and lorebook_author.username not in authors:
            authors.append(lorebook_author.username)

    return _merge_books_into_character(character, books, authors)


async def render_merged_character_data(character: SillyTavernCardV3Data,
                                       links: tuple[LorebookReference, ...],
                                       database: DatabaseService,
                                       *, character_author_name: str,
                                       ) -> SillyTavernCardV3Data:
    """Embed pinned lorebook releases for content-diff rendering only.

    Unlike merge_linked_lorebooks, this never raises and does not re-check current visibility:
    it renders what a past or new release's merged content looks like for ResourceVersion's
    content_diff. A link's release is a permanent, immutable snapshot (published resources
    cannot be deleted), so every pinned link is expected to resolve; one that nonetheless
    cannot be resolved is skipped rather than blocking the diff or the publish it belongs to.
    """
    books = []
    authors = [character_author_name] if character.character_book else []
    for link in links:
        if not link.version_id:
            continue
        version = await database.resource_version.get(link.version_id)
        document = (
            await database.silly_tavern_lorebook_data.get(version.data_id) if version else None
        )
        if not document:
            continue
        books.append(document.data)
        if link.author and link.author not in authors:
            authors.append(link.author)

    return _merge_books_into_character(character, books, authors)


def _merge_books_into_character(character: SillyTavernCardV3Data,
                                books: list,
                                authors: list[str],
                                ) -> SillyTavernCardV3Data:
    if not books:
        if not character.character_book:
            return character
        return character.model_copy(update={'character_book': character.character_book.model_copy(
            update={'author': ', '.join(authors)},
        )})
    base = character.character_book or books[0]
    extra_books = books if character.character_book else books[1:]
    linked_entries = [entry for book in extra_books for entry in book.entries]
    merged = base.model_copy(update={
        'entries': [*base.entries, *linked_entries],
        'author': ', '.join(authors),
    })
    return character.model_copy(update={'character_book': merged})


async def compute_release_content_diff(*, resource: Resource,
                                       repository: Any,
                                       database: DatabaseService,
                                       latest: ResourceVersion | None,
                                       current_data: Any,
                                       release_lorebooks: tuple[LorebookReference, ...],
                                       author_username: str | None,
                                       ) -> str | None:
    """Render the content_diff for a new release of `resource` against `latest`, if any."""
    previous_document = await repository.get(latest.data_id) if latest else None
    if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER:
        diff_current = await render_merged_character_data(
            current_data, release_lorebooks, database, character_author_name=author_username,
        )
        diff_previous = None
        if previous_document:
            diff_previous = await render_merged_character_data(
                previous_document.data, latest.linked_lorebooks, database,
                character_author_name=author_username,
            )
    else:
        diff_current = current_data
        diff_previous = previous_document.data if previous_document else None
    return build_content_diff(render_release_text(diff_previous), render_release_text(diff_current))


async def snapshot_lorebook_references(links: tuple[LorebookReference, ...],
                                       database: DatabaseService,
                                       ) -> tuple[LorebookReference, ...]:
    snapshots = []
    for link in links:
        if not link.version_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                'Character releases cannot link lorebook drafts; select a lorebook release first',
            )
        version = await database.resource_version.get(link.version_id)
        resource = await database.resource.get(link.resource_id)
        author = await database.user.get(resource.author_id) if resource else None
        if not version or not resource or version.resource_id != resource.id or not author:
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook release is invalid')
        snapshots.append(link.model_copy(update={
            'name': version.metadata.name,
            'author': author.username,
            'version': version.version,
        }))
    return tuple(snapshots)


async def resolve_download_asset(version: ResourceVersion,
                                 database: DatabaseService,
                                 ) -> tuple[str, str, str, int | None, str | None]:
    if version.artifact_object_key:
        return (
            version.artifact_object_key,
            version.artifact_content_type or 'application/octet-stream',
            version.artifact_file_name or f'{version.metadata.name}.{version.version}',
            version.artifact_byte_size,
            version.artifact_sha256,
        )
    if version.resource_type == ResourceType.IMAGE:
        document = await database.image_data.get(version.data_id)
        if document:
            return (document.object_key, document.content_type,
                    f'{version.metadata.name}.png', document.byte_size, document.sha256)
    raise HTTPException(status.HTTP_404_NOT_FOUND, 'Release artifact not found')
