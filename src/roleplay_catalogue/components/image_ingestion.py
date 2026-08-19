from asyncio import to_thread
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import (
    ImageDataDocument,
    Resource,
    ResourceLanguage,
    ResourceMetadata,
    ResourceType,
    ResourceVersion,
    ResourceVisibility,
    User,
)
from roleplay_catalogue.services import DatabaseService, StorageService


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
                                user: User,
                                database: DatabaseService,
                                storage: StorageService,
                                ) -> Resource:
    """Create (or reuse) a private-by-default image Resource, uploading its content to storage.

    Deduplicates by content hash within the calling user's own images, so re-importing the same
    picture (e.g. as a character's cover and again embedded in a lorebook) does not create copies.
    """
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
    try:
        await storage.upload(object_key, png, 'image/png')
        uploaded = True
        await storage.wait_until_available(object_key)

        async def persist_image() -> None:
            await database.resource.create(resource)
            await database.image_data.create(document)
            await database.resource_version.create(version)

        await database.transaction(persist_image)
    except Exception:
        if uploaded:
            await storage.remove(object_key)
        raise
    return resource
