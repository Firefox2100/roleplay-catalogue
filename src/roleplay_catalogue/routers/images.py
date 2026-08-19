from asyncio import to_thread
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import (
    CommonModel,
    ImageDataDocument,
    Resource,
    ResourceLanguage,
    ResourceMetadata,
    ResourceType,
    ResourceVersion,
    ResourceVisibility,
)
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from .resource_utils import (
    get_data_repository,
    get_editable_resource,
    get_owned_resource,
    get_readable_resource,
    get_readable_version,
)
from .utils import (
    AuthenticatedUserDependency,
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


def convert_to_clean_png(source: bytes) -> tuple[bytes, int, int]:
    try:
        with Image.open(BytesIO(source)) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            image.load()
            has_alpha = image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            cleaned = image.convert('RGBA' if has_alpha else 'RGB')
            width, height = cleaned.size
            output = BytesIO()
            cleaned.save(output, format='PNG', optimize=True)
            return output.getvalue(), width, height
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError('Uploaded file is not a supported image') from error


async def read_and_convert_image(file: UploadFile) -> tuple[bytes, int, int]:
    source = await file.read(CONFIG.image_max_bytes + 1)
    if len(source) > CONFIG.image_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 'Image is too large')
    try:
        return await to_thread(convert_to_clean_png, source)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


async def create_image_resource(*,
                                name: str,
                                description: str,
                                visibility: ResourceVisibility,
                                tags: list[str],
                                language: ResourceLanguage = ResourceLanguage.ENGLISH_UK,
                                file: UploadFile | None = None,
                                source: bytes | None = None,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                storage: StorageDependency,
                                ) -> Resource:
    if not name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Image name must not be blank')
    if source is None:
        if file is None:
            raise ValueError('An image file or source bytes are required')
        png, width, height = await read_and_convert_image(file)
    else:
        try:
            png, width, height = await to_thread(convert_to_clean_png, source)
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    digest = sha256(png).hexdigest()
    for existing_document in await database.image_data.list_by_sha256(digest):
        existing_resource = await database.resource.get(existing_document.resource_id)
        if existing_resource and existing_resource.author_id == user.id:
            return existing_resource

    resource = Resource(
        resourceType=ResourceType.IMAGE,
        authorId=user.id,
        metadata=ResourceMetadata(
            name=name.strip(),
            description=description.strip(),
            language=language,
            visibility=visibility,
            tags=tuple(tag.strip() for tag in tags if tag.strip()),
        ),
    )
    version_id = str(uuid4())
    object_key = f'images/{resource.id}.png'
    document = ImageDataDocument(
        resourceId=resource.id,
        resourceVersionId=version_id,
        objectKey=object_key,
        contentType='image/png',
        byteSize=len(png),
        sha256=digest,
        width=width,
        height=height,
    )
    version = ResourceVersion(
        id=version_id,
        resourceId=resource.id,
        resourceType=ResourceType.IMAGE,
        versionNumber=1,
        version='v1.0.0',
        dataId=document.id,
        metadata=resource.metadata,
        visibility=resource.metadata.visibility,
        publishedById=user.id,
    )

    uploaded = False
    resource_created = False
    data_created = False
    try:
        await storage.upload(object_key, png, 'image/png')
        uploaded = True
        await storage.wait_until_available(object_key)

        async def persist_image() -> None:
            await database.resource.create(resource)
            await database.image_data.create(document)
            await database.resource_version.create(version)

        if hasattr(database, 'transaction'):
            await database.transaction(persist_image)
        else:
            await database.resource.create(resource)
            resource_created = True
            await database.image_data.create(document)
            data_created = True
            await database.resource_version.create(version)
    except Exception:
        if data_created:
            await database.image_data.delete(document.id)
        if resource_created:
            await database.resource.delete(resource.id)
        if uploaded:
            await storage.remove(object_key)
        raise
    return resource


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
    await database.resource.update(character.model_copy(update={
        'cover_image_resource_id': image.id,
        'updated_at': utc_now(),
    }))
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
    return await database.resource.update(character.model_copy(update={
        'cover_image_resource_id': image.id,
        'updated_at': utc_now(),
    }))


@image_router.put('/{image_resource_id}/metadata', response_model=Resource)
async def update_image_metadata(image_resource_id: str,
                                payload: ImageMetadataRequest,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
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
    updated = await database.resource.update(image.model_copy(update={
        'metadata': metadata,
        'updated_at': utc_now(),
    }))
    await database.resource_version.update(version.model_copy(update={
        'metadata': metadata,
        'visibility': metadata.visibility,
    }))
    return updated


@image_router.delete('/{image_resource_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_resource(image_resource_id: str,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
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

    if hasattr(database, 'transaction'):
        await database.transaction(delete_records)
    else:
        await delete_records()
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
