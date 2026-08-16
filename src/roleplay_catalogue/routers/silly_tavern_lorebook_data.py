from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from roleplay_catalogue.models import CommonModel, ResourceType
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernLorebookDataDocument,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern.card_v3 import (
    SillyTavernCardV3LoreBook,
)
from .resource_utils import get_owned_resource, get_readable_resource
from .utils import (
    AuthenticatedUserDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
)


silly_tavern_lorebook_data_router = APIRouter(
    prefix='/data/sillytavern/lorebooks',
    tags=['SillyTavern Lorebook Data'],
)


class SillyTavernLorebookDataRequest(CommonModel):
    data: SillyTavernCardV3LoreBook = Field(...)


@silly_tavern_lorebook_data_router.post(
    '/{resource_id}',
    response_model=SillyTavernLorebookDataDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_lorebook_data(resource_id: str,
                               payload: SillyTavernLorebookDataRequest,
                               database: DatabaseDependency,
                               user: AuthenticatedUserDependency,
                               ) -> SillyTavernLorebookDataDocument:
    resource = await get_owned_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_LOREBOOK,
    )
    if resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource already has draft data')

    document = SillyTavernLorebookDataDocument(resourceId=resource.id, data=payload.data)
    await database.silly_tavern_lorebook_data.create(document)
    await database.resource.update(resource.model_copy(update={
        'draft_data_id': document.id,
        'updated_at': utc_now(),
    }))
    return document


@silly_tavern_lorebook_data_router.get(
    '/resource/{resource_id}',
    response_model=list[SillyTavernLorebookDataDocument],
)
async def list_lorebook_data(resource_id: str,
                             database: DatabaseDependency,
                             user: AuthenticatedUserDependency,
                             ) -> list[SillyTavernLorebookDataDocument]:
    await get_owned_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_LOREBOOK,
    )
    return await database.silly_tavern_lorebook_data.list_for_resource(resource_id)


@silly_tavern_lorebook_data_router.get('/{data_id}', response_model=SillyTavernLorebookDataDocument)
async def get_lorebook_data(data_id: str,
                            database: DatabaseDependency,
                            user: OptionalAuthenticatedUserDependency,
                            ) -> SillyTavernLorebookDataDocument:
    document = await database.silly_tavern_lorebook_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lorebook data not found')
    if document.resource_version_id:
        await get_readable_resource(database, document.resource_id, user)
    elif not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lorebook data not found')
    else:
        await get_owned_resource(database, document.resource_id, user)
    return document


@silly_tavern_lorebook_data_router.put('/{data_id}', response_model=SillyTavernLorebookDataDocument)
async def update_lorebook_data(data_id: str,
                               payload: SillyTavernLorebookDataRequest,
                               database: DatabaseDependency,
                               user: AuthenticatedUserDependency,
                               ) -> SillyTavernLorebookDataDocument:
    document = await database.silly_tavern_lorebook_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lorebook data not found')
    resource = await get_owned_resource(
        database, document.resource_id, user, ResourceType.SILLY_TAVERN_LOREBOOK,
    )
    if document.resource_version_id or resource.draft_data_id != document.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published data is immutable')

    updated = document.model_copy(update={'data': payload.data, 'updated_at': utc_now()})
    await database.resource.update(resource.model_copy(update={'updated_at': utc_now()}))
    return await database.silly_tavern_lorebook_data.update(updated)


@silly_tavern_lorebook_data_router.delete('/{data_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_lorebook_data(data_id: str,
                               database: DatabaseDependency,
                               user: AuthenticatedUserDependency,
                               ) -> None:
    document = await database.silly_tavern_lorebook_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lorebook data not found')
    resource = await get_owned_resource(database, document.resource_id, user)
    if document.resource_version_id or resource.draft_data_id != document.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published data is immutable')

    await database.silly_tavern_lorebook_data.delete(document.id)
    await database.resource.update(resource.model_copy(update={
        'draft_data_id': None,
        'updated_at': utc_now(),
    }))
