from asyncio import to_thread
from base64 import b64encode
from hashlib import sha256
from io import BytesIO
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from PIL import Image, PngImagePlugin
from pydantic import Field, field_validator

from roleplay_catalogue.models import CommonModel, ResourceType, ResourceVersion, ResourceVisibility
from roleplay_catalogue.models import Resource, ResourceMetadata, ResourceVersionReference
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCardV3,
    SillyTavernLorebookV3,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern.card_v3 import (
    SillyTavernCardV3Data,
    SillyTavernCardV3LoreBook,
)
from roleplay_catalogue.services import build_world_bundle
from .resource_utils import get_data_repository, get_owned_resource, get_readable_version
from .images import create_image_resource
from .utils import AuthenticatedUserDependency, DatabaseDependency, OptionalAuthenticatedUserDependency, StorageDependency


resource_version_router = APIRouter(prefix='/versions', tags=['Resource Versions'])


class PublishResourceRequest(CommonModel):
    version: str = Field(..., min_length=1, max_length=100)

    @field_validator('version')
    @classmethod
    def version_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Version must not be blank')
        return value.strip()


class VersionVisibilityRequest(CommonModel):
    visibility: ResourceVisibility


class SignedDownloadResponse(CommonModel):
    url: str
    expires_in: int = Field(..., alias='expiresIn')


def attachment_header(file_name: str) -> str:
    return f"attachment; filename*=UTF-8''{quote(file_name, safe='')}"


async def read_storage_object(storage: StorageDependency, key: str) -> bytes:
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


async def build_character_artifact(*, database: DatabaseDependency,
                                   storage: StorageDependency,
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
                                 lorebook_ids: tuple[str, ...],
                                 database: DatabaseDependency,
                                 *, published_only: bool = False,
                                 required_visibility: ResourceVisibility | None = None,
                                 ) -> SillyTavernCardV3Data:
    """Embed linked books in selection order, retaining private-book settings as the base."""
    books: list[SillyTavernCardV3LoreBook] = []
    for lorebook_id in lorebook_ids:
        resource = await database.resource.get(lorebook_id)
        if not resource or resource.resource_type != ResourceType.SILLY_TAVERN_LOREBOOK:
            raise HTTPException(status.HTTP_409_CONFLICT, 'A linked lorebook no longer exists')
        version = await database.resource_version.get_latest(resource.id)
        if published_only and version and required_visibility:
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
        document = None
        if not published_only and resource.draft_data_id:
            document = await database.silly_tavern_lorebook_data.get(resource.draft_data_id)
        if not document:
            document = (
                await database.silly_tavern_lorebook_data.get(version.data_id)
                if version else None
            )
        if not document:
            detail = 'published release' if published_only else 'content'
            raise HTTPException(status.HTTP_409_CONFLICT, f'A linked lorebook has no {detail}')
        books.append(document.data)

    if not books:
        return character
    base = character.character_book or books[0]
    linked_entries = [entry for book in books for entry in book.entries]
    if character.character_book is None:
        linked_entries = [entry for book in books[1:] for entry in book.entries]
    merged = base.model_copy(update={'entries': [*base.entries, *linked_entries]})
    return character.model_copy(update={'character_book': merged})


async def resolve_download_asset(version: ResourceVersion,
                                 database: DatabaseDependency,
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


@resource_version_router.get('/draft/{resource_id}/download')
async def export_resource_draft(resource_id: str, database: DatabaseDependency,
                                storage: StorageDependency,
                                user: AuthenticatedUserDependency) -> Response:
    resource = await get_owned_resource(database, resource_id, user)
    if resource.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
            ResourceType.WORLD_SIMULATION_WORLD,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource type cannot be exported')
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource has no draft data')
    repository = get_data_repository(database, resource.resource_type)
    draft = await repository.get(resource.draft_data_id)
    if not draft or draft.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER:
        author = await database.user.get(resource.author_id)
        if not author:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Resource author no longer exists')
        data = draft.data.model_copy(update={
            'description': resource.metadata.description,
            'tags': list(resource.metadata.tags),
            'creator': draft.data.creator or author.username,
        })
        artifact_data = await merge_linked_lorebooks(
            data, resource.linked_lorebook_resource_ids, database,
        )
        card = SillyTavernCardV3(spec='chara_card_v3', spec_version='3.0', data=artifact_data)
        artifact, content_type, extension = await build_character_artifact(
            database=database, storage=storage, card=card,
            cover_image_resource_id=resource.cover_image_resource_id,
        )
    elif resource.resource_type == ResourceType.SILLY_TAVERN_LOREBOOK:
        data = draft.data.model_copy(update={
            'name': resource.metadata.name,
            'description': resource.metadata.description,
        })
        artifact = SillyTavernLorebookV3(
            spec='lorebook_v3', data=data,
        ).model_dump_json(exclude_none=True).encode('utf-8')
        content_type, extension = 'application/json', '.json'
    else:
        data = draft.data
        artifact = await build_world_bundle(data, database, storage)
        content_type, extension = 'application/zip', '.zip'
    export_name = data.name if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER else resource.metadata.name
    file_name = f'{export_name or resource.metadata.name}.draft{extension}'
    return Response(
        artifact,
        media_type=content_type,
        headers={
            'Content-Disposition': attachment_header(file_name),
            'Cache-Control': 'no-store',
        },
    )


@resource_version_router.post('/{resource_id}', response_model=ResourceVersion,
                              status_code=status.HTTP_201_CREATED)
async def publish_resource(resource_id: str, payload: PublishResourceRequest,
                           database: DatabaseDependency, storage: StorageDependency,
                           user: AuthenticatedUserDependency) -> ResourceVersion:
    resource = await get_owned_resource(database, resource_id, user)
    if resource.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
            ResourceType.WORLD_SIMULATION_WORLD,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'This resource type cannot be published yet')
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource has no draft data')
    repository = get_data_repository(database, resource.resource_type)
    draft = await repository.get(resource.draft_data_id)
    if not draft or draft.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    version_id = str(uuid4())
    if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER:
        author = await database.user.get(resource.author_id)
        if not author:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Resource author no longer exists')
        snapshot_data = draft.data.model_copy(update={
            'description': resource.metadata.description,
            'tags': list(resource.metadata.tags),
            'creator': draft.data.creator or author.username,
            'character_version': draft.data.character_version or payload.version,
        })
        artifact_data = await merge_linked_lorebooks(
            snapshot_data, resource.linked_lorebook_resource_ids, database, published_only=True,
            required_visibility=resource.metadata.visibility,
        )
        card = SillyTavernCardV3(
            spec='chara_card_v3', spec_version='3.0', data=artifact_data,
        )
        artifact, content_type, extension = await build_character_artifact(
            database=database, storage=storage, card=card,
            cover_image_resource_id=resource.cover_image_resource_id,
        )
    elif resource.resource_type == ResourceType.SILLY_TAVERN_LOREBOOK:
        snapshot_data = draft.data.model_copy(update={
            'name': resource.metadata.name,
            'description': resource.metadata.description,
        })
        artifact = SillyTavernLorebookV3(
            spec='lorebook_v3', data=snapshot_data,
        ).model_dump_json(exclude_none=True).encode('utf-8')
        content_type, extension = 'application/json', '.json'
    else:
        snapshot_data = draft.data
        artifact = await build_world_bundle(snapshot_data, database, storage)
        content_type, extension = 'application/zip', '.zip'
    object_key = f'releases/{resource.id}/{version_id}{extension}'
    artifact_name = (
        snapshot_data.name
        if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER
        else resource.metadata.name
    )
    file_name = f'{artifact_name or resource.metadata.name}{extension}'
    snapshot = draft.model_copy(update={
        'id': str(uuid4()), 'resource_version_id': version_id,
        'created_at': utc_now(), 'updated_at': utc_now(), 'data': snapshot_data,
    })
    async def persist_release() -> ResourceVersion:
        latest = await database.resource_version.get_latest(resource.id)
        version = ResourceVersion(
            id=version_id, resourceId=resource.id, resourceType=resource.resource_type,
            versionNumber=latest.version_number + 1 if latest else 1, version=payload.version,
            dataId=snapshot.id, coverImageResourceId=resource.cover_image_resource_id,
            linkedLorebookResourceIds=resource.linked_lorebook_resource_ids,
            metadata=resource.metadata, visibility=resource.metadata.visibility,
            artifactObjectKey=object_key, artifactContentType=content_type,
            artifactFileName=file_name, artifactByteSize=len(artifact),
            artifactSha256=sha256(artifact).hexdigest(), publishedById=user.id,
            previousVersionId=latest.id if latest else None,
        )
        await repository.create(snapshot)
        return await database.resource_version.create(version)

    uploaded = False
    try:
        await storage.upload(object_key, artifact, content_type)
        uploaded = True
        await storage.wait_until_available(object_key)
        if hasattr(database, 'transaction'):
            return await database.transaction(persist_release)
        return await persist_release()
    except Exception:
        if uploaded:
            await storage.remove(object_key)
        raise


@resource_version_router.get('/resource/{resource_id}', response_model=list[ResourceVersion])
async def list_resource_versions(resource_id: str, database: DatabaseDependency,
                                 user: OptionalAuthenticatedUserDependency,
                                 offset: int = Query(0, ge=0),
                                 limit: int = Query(50, ge=1, le=100)) -> list[ResourceVersion]:
    resource = await database.resource.get(resource_id)
    if not resource:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
    versions = await database.resource_version.list_for_resource(resource_id, offset, limit)
    if user and resource.author_id == user.id:
        return versions
    allowed = {ResourceVisibility.PUBLIC}
    if user:
        allowed.add(ResourceVisibility.AUTHENTICATED)
    return [version for version in versions if version.visibility in allowed]


@resource_version_router.patch('/{version_id}/visibility', response_model=ResourceVersion)
async def update_version_visibility(version_id: str, payload: VersionVisibilityRequest,
                                    database: DatabaseDependency,
                                    user: AuthenticatedUserDependency) -> ResourceVersion:
    version = await database.resource_version.get(version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    await get_owned_resource(database, version.resource_id, user)
    return await database.resource_version.update(
        version.model_copy(update={'visibility': payload.visibility}),
    )


@resource_version_router.get('/{version_id}/data')
async def get_resource_version_data(version_id: str, database: DatabaseDependency,
                                    user: OptionalAuthenticatedUserDependency):
    version = await get_readable_version(database, version_id, user)
    document = await get_data_repository(database, version.resource_type).get(version.data_id)
    if not document or document.resource_version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version data not found')
    return document


@resource_version_router.get('/{version_id}/signed-download', response_model=SignedDownloadResponse)
async def create_signed_download(version_id: str, database: DatabaseDependency,
                                 storage: StorageDependency,
                                 user: OptionalAuthenticatedUserDependency) -> SignedDownloadResponse:
    version = await get_readable_version(database, version_id, user)
    key, _content_type, file_name, _byte_size, _digest = await resolve_download_asset(
        version, database,
    )
    return SignedDownloadResponse(
        url=await storage.create_signed_download_url(key, file_name),
        expiresIn=storage.signed_url_expiry,
    )


@resource_version_router.post('/{version_id}/fork', response_model=Resource,
                              status_code=status.HTTP_201_CREATED)
async def fork_resource_version(version_id: str, database: DatabaseDependency,
                                storage: StorageDependency,
                                user: AuthenticatedUserDependency) -> Resource:
    version = await get_readable_version(database, version_id, user)
    if version.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
            ResourceType.WORLD_SIMULATION_WORLD,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'This release type cannot be forked')
    source = await database.resource.get(version.resource_id)
    repository = get_data_repository(database, version.resource_type)
    snapshot = await repository.get(version.data_id)
    if not source or not snapshot or snapshot.resource_version_id != version.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Release snapshot is invalid')

    fork_name = f'Forked from {version.metadata.name}'
    cover_image_resource_id = version.cover_image_resource_id
    created_cover = None
    if cover_image_resource_id:
        source_cover = await database.resource.get(cover_image_resource_id)
        if not source_cover or source_cover.resource_type != ResourceType.IMAGE:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Release cover image is missing')
        if source_cover.author_id != user.id:
            image_version = await database.resource_version.get_latest(source_cover.id)
            image_document = (
                await database.image_data.get(image_version.data_id) if image_version else None
            )
            if not image_document:
                raise HTTPException(status.HTTP_409_CONFLICT, 'Release cover image is missing')
            existing_owned_cover = None
            for candidate in await database.image_data.list_by_sha256(image_document.sha256):
                candidate_resource = await database.resource.get(candidate.resource_id)
                if candidate_resource and candidate_resource.author_id == user.id:
                    existing_owned_cover = candidate_resource
                    break
            if existing_owned_cover:
                cover_image_resource_id = existing_owned_cover.id
            else:
                cover_bytes = await read_storage_object(storage, image_document.object_key)
                created_cover = await create_image_resource(
                    name=f'Cover image for {fork_name}',
                    description='',
                    visibility=ResourceVisibility.PRIVATE,
                    tags=[],
                    source=cover_bytes,
                    user=user,
                    database=database,
                    storage=storage,
                )
                cover_image_resource_id = created_cover.id

    now = utc_now()
    draft = snapshot.model_copy(update={
        'id': str(uuid4()),
        'resource_id': '',
        'resource_version_id': None,
        'created_at': now,
        'updated_at': now,
    })
    fork = Resource(
        resourceType=version.resource_type,
        authorId=user.id,
        metadata=ResourceMetadata(
            name=fork_name,
            description=version.metadata.description,
            visibility=ResourceVisibility.PRIVATE,
            tags=version.metadata.tags,
        ),
        draftDataId=draft.id,
        coverImageResourceId=cover_image_resource_id,
        linkedLorebookResourceIds=version.linked_lorebook_resource_ids,
        forkedFrom=ResourceVersionReference(
            resourceId=version.resource_id,
            versionId=version.id,
        ),
    )
    draft = draft.model_copy(update={'resource_id': fork.id})
    try:
        await database.resource.create(fork)
        try:
            await repository.create(draft)
        except Exception:
            await database.resource.delete(fork.id)
            raise
        return fork
    except Exception:
        if created_cover:
            image_version = await database.resource_version.get_latest(created_cover.id)
            image_document = (
                await database.image_data.get(image_version.data_id) if image_version else None
            )
            if image_document:
                await storage.remove(image_document.object_key)
                await database.image_data.delete(image_document.id)
            if image_version:
                await database.resource_version.delete(image_version.id)
            await database.resource.delete(created_cover.id)
        raise


@resource_version_router.get('/{version_id}/download')
async def download_resource_version(version_id: str, database: DatabaseDependency,
                                    storage: StorageDependency,
                                    request: Request,
                                    user: OptionalAuthenticatedUserDependency):
    version = await get_readable_version(database, version_id, user)
    key, content_type, file_name, byte_size, digest = await resolve_download_asset(
        version, database,
    )
    cache_control = (
        'public, max-age=31536000, immutable'
        if version.visibility == ResourceVisibility.PUBLIC
        else 'private, no-cache'
    )
    headers = {
        'Content-Disposition': attachment_header(file_name),
        'Cache-Control': cache_control,
    }
    if digest:
        etag = f'"{digest}"'
        headers['ETag'] = etag
        requested_etags = {part.strip() for part in request.headers.get('if-none-match', '').split(',')}
        if etag in requested_etags or '*' in requested_etags:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    if byte_size is not None:
        headers['Content-Length'] = str(byte_size)
    return StreamingResponse(storage.fetch(key), media_type=content_type, headers=headers)


@resource_version_router.get('/{version_id}', response_model=ResourceVersion)
async def get_resource_version(version_id: str, database: DatabaseDependency,
                               user: OptionalAuthenticatedUserDependency) -> ResourceVersion:
    return await get_readable_version(database, version_id, user)
