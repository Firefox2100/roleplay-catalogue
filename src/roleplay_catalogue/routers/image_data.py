from fastapi import APIRouter, HTTPException, status
from roleplay_catalogue.models import ImageData, ImageDataDocument, ResourceType
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from .resource_utils import get_owned_resource, get_readable_resource
from .utils import (
    AuthenticatedUserDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
)


image_data_router = APIRouter(
    prefix='/data/images',
    tags=['Image Data'],
)


@image_data_router.post(
    '/{resource_id}',
    response_model=ImageDataDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_image_data(resource_id: str,
                            payload: ImageData,
                            database: DatabaseDependency,
                            user: AuthenticatedUserDependency,
                            ) -> ImageDataDocument:
    resource = await get_owned_resource(database, resource_id, user, ResourceType.IMAGE)
    if resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource already has image data')
    if await database.resource_version.exists_for_resource(resource.id):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published image resources are immutable')

    document = ImageDataDocument(
        resourceId=resource.id,
        **payload.model_dump(by_alias=True),
    )
    await database.image_data.create(document)
    await database.resource.update(resource.model_copy(update={
        'draft_data_id': document.id,
        'updated_at': utc_now(),
    }))
    return document


@image_data_router.get('/resource/{resource_id}', response_model=list[ImageDataDocument])
async def list_image_data(resource_id: str,
                          database: DatabaseDependency,
                          user: AuthenticatedUserDependency,
                          ) -> list[ImageDataDocument]:
    await get_owned_resource(database, resource_id, user, ResourceType.IMAGE)
    return await database.image_data.list_for_resource(resource_id)


@image_data_router.get('/{data_id}', response_model=ImageDataDocument)
async def get_image_data(data_id: str,
                         database: DatabaseDependency,
                         user: OptionalAuthenticatedUserDependency,
                         ) -> ImageDataDocument:
    document = await database.image_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image data not found')
    if document.resource_version_id:
        await get_readable_resource(database, document.resource_id, user)
    elif not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image data not found')
    else:
        await get_owned_resource(database, document.resource_id, user)
    return document


@image_data_router.delete('/{data_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_data(data_id: str,
                            database: DatabaseDependency,
                            user: AuthenticatedUserDependency,
                            ) -> None:
    document = await database.image_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Image data not found')
    resource = await get_owned_resource(database, document.resource_id, user, ResourceType.IMAGE)
    if document.resource_version_id or resource.draft_data_id != document.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published data is immutable')

    async def delete_records() -> None:
        await database.image_data.delete(document.id)
        await database.resource.update(resource.model_copy(update={
            'draft_data_id': None,
            'updated_at': utc_now(),
        }))

    if hasattr(database, 'transaction'):
        await database.transaction(delete_records)
    else:
        await delete_records()
