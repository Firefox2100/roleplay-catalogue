from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from roleplay_catalogue.models import CommonModel, ResourceType
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCharacterData,
    SillyTavernCharacterDataDocument,
)
from .resource_utils import get_owned_resource, get_readable_resource
from .utils import (
    AuthenticatedUserDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
)


silly_tavern_character_data_router = APIRouter(
    prefix='/data/sillytavern/characters',
    tags=['SillyTavern Character Data'],
)


class SillyTavernCharacterDataRequest(CommonModel):
    data: SillyTavernCharacterData = Field(...)


@silly_tavern_character_data_router.post(
    '/{resource_id}',
    response_model=SillyTavernCharacterDataDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_character_data(resource_id: str,
                                payload: SillyTavernCharacterDataRequest,
                                database: DatabaseDependency,
                                user: AuthenticatedUserDependency,
                                ) -> SillyTavernCharacterDataDocument:
    resource = await get_owned_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_CHARACTER,
    )
    if resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource already has draft data')

    document = SillyTavernCharacterDataDocument(resourceId=resource.id, data=payload.data)
    await database.silly_tavern_character_data.create(document)
    await database.resource.update(resource.model_copy(update={
        'draft_data_id': document.id,
        'updated_at': utc_now(),
    }))
    return document


@silly_tavern_character_data_router.get(
    '/resource/{resource_id}',
    response_model=list[SillyTavernCharacterDataDocument],
)
async def list_character_data(resource_id: str,
                              database: DatabaseDependency,
                              user: AuthenticatedUserDependency,
                              ) -> list[SillyTavernCharacterDataDocument]:
    await get_owned_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_CHARACTER,
    )
    return await database.silly_tavern_character_data.list_for_resource(resource_id)


@silly_tavern_character_data_router.get(
    '/{data_id}',
    response_model=SillyTavernCharacterDataDocument,
)
async def get_character_data(data_id: str,
                             database: DatabaseDependency,
                             user: OptionalAuthenticatedUserDependency,
                             ) -> SillyTavernCharacterDataDocument:
    document = await database.silly_tavern_character_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Character data not found')
    if document.resource_version_id:
        await get_readable_resource(database, document.resource_id, user)
    elif not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Character data not found')
    else:
        await get_owned_resource(database, document.resource_id, user)
    return document


@silly_tavern_character_data_router.put(
    '/{data_id}',
    response_model=SillyTavernCharacterDataDocument,
)
async def update_character_data(data_id: str,
                                payload: SillyTavernCharacterDataRequest,
                                database: DatabaseDependency,
                                user: AuthenticatedUserDependency,
                                ) -> SillyTavernCharacterDataDocument:
    document = await database.silly_tavern_character_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Character data not found')
    resource = await get_owned_resource(
        database, document.resource_id, user, ResourceType.SILLY_TAVERN_CHARACTER,
    )
    if document.resource_version_id or resource.draft_data_id != document.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published data is immutable')

    updated = document.model_copy(update={'data': payload.data, 'updated_at': utc_now()})
    await database.resource.update(resource.model_copy(update={'updated_at': utc_now()}))
    return await database.silly_tavern_character_data.update(updated)


@silly_tavern_character_data_router.delete('/{data_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_character_data(data_id: str,
                                database: DatabaseDependency,
                                user: AuthenticatedUserDependency,
                                ) -> None:
    document = await database.silly_tavern_character_data.get(data_id)
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Character data not found')
    resource = await get_owned_resource(database, document.resource_id, user)
    if document.resource_version_id or resource.draft_data_id != document.id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Published data is immutable')

    await database.silly_tavern_character_data.delete(document.id)
    await database.resource.update(resource.model_copy(update={
        'draft_data_id': None,
        'updated_at': utc_now(),
    }))
