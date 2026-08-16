from asyncio import to_thread
from base64 import b64encode
from hashlib import sha256
from io import BytesIO
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from PIL import Image, PngImagePlugin
from pydantic import Field, field_validator

from roleplay_catalogue.models import CommonModel, ResourceType, ResourceVersion, ResourceVisibility
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import SillyTavernCardV3
from .resource_utils import get_data_repository, get_owned_resource, get_readable_version
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


@resource_version_router.get('/draft/{resource_id}/download')
async def export_character_draft(resource_id: str, database: DatabaseDependency,
                                 storage: StorageDependency,
                                 user: AuthenticatedUserDependency) -> Response:
    resource = await get_owned_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_CHARACTER,
    )
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource has no draft data')
    draft = await database.silly_tavern_character_data.get(resource.draft_data_id)
    author = await database.user.get(resource.author_id)
    if not draft or draft.resource_version_id or not author:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    data = draft.data.model_copy(update={
        'description': resource.metadata.description,
        'tags': list(resource.metadata.tags),
        'creator': draft.data.creator or author.username,
    })
    card = SillyTavernCardV3(spec='chara_card_v3', spec_version='3.0', data=data)
    artifact, content_type, extension = await build_character_artifact(
        database=database, storage=storage, card=card,
        cover_image_resource_id=resource.cover_image_resource_id,
    )
    file_name = f'{data.name or resource.metadata.name}.draft{extension}'
    return Response(
        artifact,
        media_type=content_type,
        headers={'Content-Disposition': attachment_header(file_name)},
    )


@resource_version_router.post('/{resource_id}', response_model=ResourceVersion,
                              status_code=status.HTTP_201_CREATED)
async def publish_resource(resource_id: str, payload: PublishResourceRequest,
                           database: DatabaseDependency, storage: StorageDependency,
                           user: AuthenticatedUserDependency) -> ResourceVersion:
    resource = await get_owned_resource(database, resource_id, user)
    if resource.resource_type != ResourceType.SILLY_TAVERN_CHARACTER:
        raise HTTPException(status.HTTP_409_CONFLICT, 'This resource type cannot be published yet')
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource has no draft data')
    repository = get_data_repository(database, resource.resource_type)
    draft = await repository.get(resource.draft_data_id)
    if not draft or draft.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    author = await database.user.get(resource.author_id)
    if not author:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource author no longer exists')

    latest = await database.resource_version.get_latest(resource.id)
    version_id = str(uuid4())
    snapshot_data = draft.data.model_copy(update={
        'description': resource.metadata.description,
        'tags': list(resource.metadata.tags),
        'creator': draft.data.creator or author.username,
        'character_version': draft.data.character_version or payload.version,
    })
    card = SillyTavernCardV3(spec='chara_card_v3', spec_version='3.0', data=snapshot_data)
    artifact, content_type, extension = await build_character_artifact(
        database=database, storage=storage, card=card,
        cover_image_resource_id=resource.cover_image_resource_id,
    )
    object_key = f'releases/{resource.id}/{version_id}{extension}'
    file_name = f'{snapshot_data.name or resource.metadata.name}{extension}'
    snapshot = draft.model_copy(update={
        'id': str(uuid4()), 'resource_version_id': version_id,
        'created_at': utc_now(), 'updated_at': utc_now(), 'data': snapshot_data,
    })
    version = ResourceVersion(
        id=version_id, resourceId=resource.id, resourceType=resource.resource_type,
        versionNumber=latest.version_number + 1 if latest else 1, version=payload.version,
        dataId=snapshot.id, coverImageResourceId=resource.cover_image_resource_id,
        metadata=resource.metadata, visibility=resource.metadata.visibility,
        artifactObjectKey=object_key, artifactContentType=content_type,
        artifactFileName=file_name, artifactByteSize=len(artifact),
        artifactSha256=sha256(artifact).hexdigest(), publishedById=user.id,
        previousVersionId=latest.id if latest else None,
    )
    uploaded = snapshot_created = False
    try:
        await storage.upload(object_key, artifact, content_type)
        uploaded = True
        await storage.wait_until_available(object_key)
        await repository.create(snapshot)
        snapshot_created = True
        return await database.resource_version.create(version)
    except Exception:
        if snapshot_created:
            await repository.delete(snapshot.id)
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


@resource_version_router.get('/{version_id}/download')
async def download_resource_version(version_id: str, database: DatabaseDependency,
                                    storage: StorageDependency,
                                    user: OptionalAuthenticatedUserDependency):
    version = await get_readable_version(database, version_id, user)
    if version.artifact_object_key:
        key = version.artifact_object_key
        content_type = version.artifact_content_type or 'application/octet-stream'
        file_name = version.artifact_file_name or f'{version.metadata.name}.{version.version}'
        byte_size = version.artifact_byte_size
    elif version.resource_type == ResourceType.IMAGE:
        document = await database.image_data.get(version.data_id)
        if not document:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image data not found')
        key = document.object_key
        content_type = document.content_type
        file_name = f'{version.metadata.name}.png'
        byte_size = document.byte_size
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Release artifact not found')
    headers = {'Content-Disposition': attachment_header(file_name)}
    if byte_size is not None:
        headers['Content-Length'] = str(byte_size)
    return StreamingResponse(storage.fetch(key), media_type=content_type, headers=headers)


@resource_version_router.get('/{version_id}', response_model=ResourceVersion)
async def get_resource_version(version_id: str, database: DatabaseDependency,
                               user: OptionalAuthenticatedUserDependency) -> ResourceVersion:
    return await get_readable_version(database, version_id, user)
