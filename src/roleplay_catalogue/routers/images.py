from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import Field

from roleplay_catalogue.models import (
    CommonModel,
    Resource,
    ResourceLanguage,
    ResourceMetadata,
    ResourceType,
    ResourceVisibility,
)
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.components import (
    create_image_resource,
    etag_header,
    get_data_repository,
    get_editable_resource,
    get_owned_resource,
    get_readable_resource,
    get_readable_version,
    parse_if_match,
    raise_stale_revision,
)
from .utils import (
    AuthenticatedUserDependency,
    CacheDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
    StorageDependency,
)


image_router = APIRouter(prefix='/images', tags=['Images'])


class CoverImageRequest(CommonModel):
    image_resource_id: str = Field(..., alias='imageResourceId')


class ImageMetadataRequest(CommonModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field('', max_length=10_000)
    language: ResourceLanguage | None = None
    visibility: ResourceVisibility
    tags: list[str] = Field(default_factory=list, max_length=50)


@image_router.post('', response_model=Resource, status_code=status.HTTP_201_CREATED)
async def upload_image_resource(user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                storage: StorageDependency,
                                name: str = Form(..., min_length=1, max_length=200),
                                description: str = Form('', max_length=10_000),
                                visibility: ResourceVisibility = Form(ResourceVisibility.PRIVATE),
                                tags: list[str] = Form(default_factory=list),
                                language: ResourceLanguage = Form(ResourceLanguage.ENGLISH_UK),
                                file: UploadFile = File(...),
                                ) -> Resource:
    return await create_image_resource(
        name=name,
        description=description,
        visibility=visibility,
        tags=tags,
        language=language,
        file=file,
        user=user,
        database=database,
        storage=storage,
    )


@image_router.post('/covers/{character_resource_id}', response_model=Resource)
async def upload_character_cover(character_resource_id: str,
                                 file: UploadFile,
                                 user: AuthenticatedUserDependency,
                                 database: DatabaseDependency,
                                 storage: StorageDependency,
                                 ) -> Resource:
    character = await get_editable_resource(database, character_resource_id, user)
    if character.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource type does not support covers')
    image = await create_image_resource(
        name=f'Cover image for {character.metadata.name}',
        description='',
        visibility=character.metadata.visibility,
        tags=[],
        file=file,
        user=user,
        database=database,
        storage=storage,
    )
    await database.resource.apply_update(character.id, {'coverImageResourceId': image.id})
    return image


@image_router.put('/covers/{character_resource_id}', response_model=Resource)
async def select_character_cover(character_resource_id: str,
                                 payload: CoverImageRequest,
                                 user: AuthenticatedUserDependency,
                                 database: DatabaseDependency,
                                 ) -> Resource:
    character = await get_editable_resource(database, character_resource_id, user)
    if character.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource type does not support covers')
    image = await get_editable_resource(
        database, payload.image_resource_id, user, ResourceType.IMAGE,
    )
    if not await database.resource_version.get_latest(image.id):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Image resource has no content')
    updated = await database.resource.apply_update(character.id, {'coverImageResourceId': image.id})
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
    return updated


@image_router.delete('/covers/{character_resource_id}', response_model=Resource)
async def clear_character_cover(character_resource_id: str,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                ) -> Resource:
    character = await get_editable_resource(database, character_resource_id, user)
    if character.resource_type not in (
            ResourceType.SILLY_TAVERN_CHARACTER,
            ResourceType.SILLY_TAVERN_LOREBOOK,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource type does not support covers')
    updated = await database.resource.apply_update(
        character.id, {'coverImageResourceId': None},
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
    return updated


@image_router.put('/{image_resource_id}/metadata', response_model=Resource)
async def update_image_metadata(image_resource_id: str,
                                payload: ImageMetadataRequest,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                response: Response,
                                if_match: str | None = Header(None, alias='If-Match'),
                                ) -> Resource:
    image = await get_editable_resource(database, image_resource_id, user, ResourceType.IMAGE)
    if not payload.name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Image name must not be blank')
    metadata = ResourceMetadata(
        name=payload.name.strip(),
        description=payload.description.strip(),
        language=payload.language or image.metadata.language,
        visibility=payload.visibility,
        tags=tuple(tag.strip() for tag in payload.tags if tag.strip()),
    )
    version = await database.resource_version.get_latest(image.id)
    if not version:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Image resource has no immutable version')
    expected_revision = parse_if_match(if_match)
    updated = await database.resource.update_if_match(
        image.model_copy(update={'metadata': metadata, 'updated_at': utc_now()}),
        expected_revision,
    )
    if updated is None:
        current = await database.resource.get(image_resource_id)
        if not current:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
        raise_stale_revision(current)
    await database.resource_version.update(version.model_copy(update={
        'metadata': metadata,
        'visibility': metadata.visibility,
    }))
    response.headers['ETag'] = etag_header(updated.revision)
    return updated


@image_router.delete('/{image_resource_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_resource(image_resource_id: str,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                cache: CacheDependency,
                                storage: StorageDependency,
                                force: bool = Query(False),
                                ) -> None:
    image = await get_owned_resource(database, image_resource_id, user, ResourceType.IMAGE)
    referencing_versions = [
        version for version in await database.resource_version.list_by_cover(image.id)
        if version.resource_type != ResourceType.IMAGE
    ]
    world_references = await database.world_data.list_referencing_image(image.id)
    if (referencing_versions or world_references) and not force:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Image is referenced by another resource; retry with force=true to remove it',
        )
    object_keys: set[str] = set()

    async def delete_records() -> None:
        current_references = [
            version for version in await database.resource_version.list_by_cover(image.id)
            if version.resource_type != ResourceType.IMAGE
        ]
        current_world_references = await database.world_data.list_referencing_image(image.id)
        if (current_references or current_world_references) and not force:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                'Image is referenced by another resource; retry with force=true to remove it',
            )
        if force:
            for version in current_references:
                if version.artifact_object_key:
                    object_keys.add(version.artifact_object_key)
                await get_data_repository(database, version.resource_type).delete(version.data_id)
                await database.resource_version.delete(version.id)
            for document in current_world_references:
                if document.resource_version_id:
                    version = await database.resource_version.get(document.resource_version_id)
                    if version:
                        if version.artifact_object_key:
                            object_keys.add(version.artifact_object_key)
                        await database.resource_version.delete(version.id)
                    await database.world_data.delete(document.id)
                    continue
                media = [
                    reference.model_copy(update={'image_resource_id': None})
                    if reference.image_resource_id == image.id else reference
                    for reference in document.data.media
                ]
                await database.world_data.update(document.model_copy(update={
                    'data': document.data.model_copy(update={'media': media}),
                    'updated_at': utc_now(),
                }))
        await database.resource.clear_cover_reference(image.id)
        for version in await database.resource_version.list_all_for_resource(image.id):
            document = await database.image_data.get(version.data_id)
            if document:
                object_keys.add(document.object_key)
            await database.image_data.delete(version.data_id)
            await database.resource_version.delete(version.id)
        await database.resource.delete(image.id)

    await database.transaction(delete_records)
    await cache.resource_metrics.delete(image.id)
    for object_key in object_keys:
        await storage.remove(object_key)


async def image_response(image: Resource,
                         database: DatabaseDependency,
                         storage: StorageDependency,
                         request: Request,
                         cache_control: str,
                         ) -> Response:
    version = await database.resource_version.get_latest(image.id)
    document = await database.image_data.get(version.data_id) if version else None
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image not found')
    etag = f'"{document.sha256}"'
    headers = {'ETag': etag, 'Cache-Control': cache_control}
    requested_etags = {
        part.strip() for part in request.headers.get('if-none-match', '').split(',')
    }
    if etag in requested_etags or '*' in requested_etags:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    headers['Content-Length'] = str(document.byte_size)
    return StreamingResponse(
        storage.fetch(document.object_key),
        media_type=document.content_type,
        headers=headers,
    )


@image_router.get('/covers/resources/{resource_id}')
async def fetch_resource_cover(resource_id: str,
                               request: Request,
                               user: OptionalAuthenticatedUserDependency,
                               database: DatabaseDependency,
                               storage: StorageDependency,
                               ) -> Response:
    resource = await get_readable_resource(database, resource_id, user)
    if not resource.cover_image_resource_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource has no cover image')
    image = await database.resource.get(resource.cover_image_resource_id)
    if not image or image.resource_type != ResourceType.IMAGE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Cover image not found')
    cache_control = (
        'public, max-age=60, must-revalidate'
        if resource.metadata.visibility == ResourceVisibility.PUBLIC
        else 'private, no-cache'
    )
    return await image_response(image, database, storage, request, cache_control)


@image_router.get('/covers/versions/{version_id}')
async def fetch_version_cover(version_id: str,
                              request: Request,
                              user: OptionalAuthenticatedUserDependency,
                              database: DatabaseDependency,
                              storage: StorageDependency,
                              ) -> Response:
    version = await get_readable_version(database, version_id, user)
    if not version.cover_image_resource_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Release has no cover image')
    image = await database.resource.get(version.cover_image_resource_id)
    if not image or image.resource_type != ResourceType.IMAGE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Cover image not found')
    cache_control = (
        'public, max-age=31536000, immutable'
        if version.visibility == ResourceVisibility.PUBLIC
        else 'private, no-cache'
    )
    return await image_response(image, database, storage, request, cache_control)


@image_router.get('/{image_resource_id}/content')
async def fetch_image(image_resource_id: str,
                      request: Request,
                      user: OptionalAuthenticatedUserDependency,
                      database: DatabaseDependency,
                      storage: StorageDependency,
                      ) -> Response:
    image = await get_readable_resource(database, image_resource_id, user)
    if image.resource_type != ResourceType.IMAGE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image not found')
    cache_control = (
        'public, max-age=31536000, immutable'
        if image.metadata.visibility == ResourceVisibility.PUBLIC
        else 'private, no-cache'
    )
    return await image_response(image, database, storage, request, cache_control)
