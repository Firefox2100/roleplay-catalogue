from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ConfigDict, Field, field_validator

from roleplay_catalogue.models import (
    CommonModel,
    ImageData,
    ImageDataDocument,
    Resource,
    ResourceMetadata,
    ResourceType,
    ResourceVisibility,
)
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCharacterData,
    SillyTavernCharacterDataDocument,
    SillyTavernLorebookDataDocument,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern.card_v3 import (
    SillyTavernCardV3LoreBook,
)
from .resource_utils import get_data_repository, get_owned_resource, get_readable_resource
from .utils import (
    AuthenticatedUserDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
)


resource_router = APIRouter(
    prefix='/resources',
    tags=['Resources'],
)


class ResourceCreateRequest(CommonModel):
    model_config = ConfigDict(extra='forbid', serialize_by_alias=True)

    resource_type: ResourceType = Field(..., alias='resourceType')
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field('', max_length=10_000)
    visibility: ResourceVisibility = ResourceVisibility.PRIVATE
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Resource name must not be blank')
        return value


class ResourceUpdateRequest(CommonModel):
    model_config = ConfigDict(extra='forbid', serialize_by_alias=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field('', max_length=10_000)
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator('name')
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Resource name must not be blank')
        return value


class ResourceDataUpsertRequest(CommonModel):
    data: dict[str, Any] = Field(
        ...,
        description='Canonical payload; its schema is selected by the resource type',
    )


class ResourceListItem(Resource):
    author_username: str = Field(..., alias='authorUsername')


ResourceDataResponse = (
    SillyTavernCharacterDataDocument |
    SillyTavernLorebookDataDocument |
    ImageDataDocument
)


def validate_resource_data(resource_type: ResourceType,
                           data: dict[str, Any],
                           ) -> SillyTavernCharacterData | SillyTavernCardV3LoreBook | ImageData:
    models = {
        ResourceType.SILLY_TAVERN_CHARACTER: SillyTavernCharacterData,
        ResourceType.SILLY_TAVERN_LOREBOOK: SillyTavernCardV3LoreBook,
        ResourceType.IMAGE: ImageData,
    }
    try:
        return models[resource_type].model_validate(data)
    except ValueError as error:
        if hasattr(error, 'errors'):
            raise RequestValidationError(error.errors()) from error
        raise


def create_data_document(resource: Resource,
                         data: SillyTavernCharacterData | SillyTavernCardV3LoreBook | ImageData,
                         ) -> ResourceDataResponse:
    models = {
        ResourceType.SILLY_TAVERN_CHARACTER: SillyTavernCharacterDataDocument,
        ResourceType.SILLY_TAVERN_LOREBOOK: SillyTavernLorebookDataDocument,
        ResourceType.IMAGE: ImageDataDocument,
    }
    if resource.resource_type == ResourceType.IMAGE:
        return models[resource.resource_type](
            resourceId=resource.id,
            **data.model_dump(by_alias=True),
        )
    return models[resource.resource_type](resourceId=resource.id, data=data)


@resource_router.post('', response_model=Resource, status_code=status.HTTP_201_CREATED)
async def create_resource(payload: ResourceCreateRequest,
                          user: AuthenticatedUserDependency,
                          database: DatabaseDependency,
                          ) -> Resource:
    if payload.resource_type == ResourceType.IMAGE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Image resources must be created together with an uploaded file',
        )
    resource = Resource(
        resourceType=payload.resource_type,
        authorId=user.id,
        metadata=ResourceMetadata(
            name=payload.name,
            description=payload.description.strip(),
            visibility=payload.visibility,
            tags=tuple(tag.strip() for tag in payload.tags if tag.strip()),
        ),
    )
    return await database.resource.create(resource)


@resource_router.get('', response_model=list[ResourceListItem])
async def list_resources(database: DatabaseDependency,
                         user: OptionalAuthenticatedUserDependency,
                         offset: int = Query(0, ge=0),
                         limit: int = Query(50, ge=1, le=100),
                         resource_type: ResourceType | None = Query(
                             None,
                             alias='resourceType',
                         ),
                         tags: list[str] | None = Query(None),
                         author: str | None = Query(None, min_length=1, max_length=100),
                         published_only: bool = Query(False, alias='publishedOnly'),
                         search_string: str | None = Query(None, max_length=200),
                         ) -> list[ResourceListItem]:
    author_id = None
    if author:
        author_user = await database.user.get_by_username(author.strip())
        if not author_user:
            return []
        author_id = author_user.id

    normalised_tags = list(dict.fromkeys(
        tag.strip() for tag in (tags or []) if tag.strip()
    ))
    published_resource_ids = None
    if published_only:
        published_resource_ids = await database.resource_version.list_published_resource_ids()
    resources = await database.resource.list_visible(
        user.id if user else None,
        offset,
        limit,
        resource_type=resource_type,
        tags=normalised_tags,
        author_id=author_id,
        published_resource_ids=published_resource_ids,
        search_string=search_string.strip() if search_string else None,
    )
    users = await database.user.get_many({resource.author_id for resource in resources})
    return [ResourceListItem(
        **resource.model_dump(by_alias=True),
        authorUsername=users[resource.author_id].username,
    ) for resource in resources if resource.author_id in users]


@resource_router.get('/tags', response_model=list[str])
async def suggest_resource_tags(database: DatabaseDependency,
                                user: OptionalAuthenticatedUserDependency,
                                search: str = Query('', max_length=100),
                                limit: int = Query(10, ge=1, le=25),
                                ) -> list[str]:
    return await database.resource.suggest_tags(
        user.id if user else None,
        search.strip(),
        limit,
    )


@resource_router.get('/{resource_id}', response_model=ResourceListItem)
async def get_resource(resource_id: str,
                       database: DatabaseDependency,
                       user: OptionalAuthenticatedUserDependency,
                       ) -> ResourceListItem:
    resource = await get_readable_resource(database, resource_id, user)
    author = await database.user.get(resource.author_id)
    if not author:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource author not found')
    return ResourceListItem(
        **resource.model_dump(by_alias=True),
        authorUsername=author.username,
    )


@resource_router.get('/{resource_id}/data', response_model=ResourceDataResponse)
async def get_resource_data(resource_id: str,
                            database: DatabaseDependency,
                            user: AuthenticatedUserDependency,
                            ) -> ResourceDataResponse:
    resource = await get_owned_resource(database, resource_id, user)
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource has no draft data')

    document = await get_data_repository(
        database, resource.resource_type,
    ).get(resource.draft_data_id)
    if not document or document.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    return document


@resource_router.put('/{resource_id}/data', response_model=ResourceDataResponse)
async def upsert_resource_data(resource_id: str,
                               payload: ResourceDataUpsertRequest,
                               database: DatabaseDependency,
                               user: AuthenticatedUserDependency,
                               ) -> ResourceDataResponse:
    resource = await get_owned_resource(database, resource_id, user)
    data = validate_resource_data(resource.resource_type, payload.data)
    repository = get_data_repository(database, resource.resource_type)

    if not resource.draft_data_id:
        document = create_data_document(resource, data)
        await repository.create(document)
        await database.resource.update(resource.model_copy(update={
            'draft_data_id': document.id,
            'updated_at': utc_now(),
        }))
        return document

    document = await repository.get(resource.draft_data_id)
    if not document or document.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')
    if resource.resource_type == ResourceType.IMAGE:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Image data is immutable')

    updated = document.model_copy(update={'data': data, 'updated_at': utc_now()})
    await database.resource.update(resource.model_copy(update={'updated_at': utc_now()}))
    return await repository.update(updated)


@resource_router.put('/{resource_id}', response_model=Resource)
async def update_resource(resource_id: str,
                          payload: ResourceUpdateRequest,
                          database: DatabaseDependency,
                          user: AuthenticatedUserDependency,
                          ) -> Resource:
    resource = await get_owned_resource(database, resource_id, user)
    updated = resource.model_copy(update={
        'metadata': ResourceMetadata(
            name=payload.name,
            description=payload.description.strip(),
            visibility=resource.metadata.visibility,
            tags=tuple(tag.strip() for tag in payload.tags if tag.strip()),
        ),
        'updated_at': utc_now(),
    })
    return await database.resource.update(updated)


@resource_router.delete('/{resource_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: str,
                          database: DatabaseDependency,
                          user: AuthenticatedUserDependency,
                          ) -> None:
    resource = await get_owned_resource(database, resource_id, user)
    if await database.resource_version.exists_for_resource(resource.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Published resources cannot be deleted',
        )

    if resource.draft_data_id:
        repository = get_data_repository(database, resource.resource_type)
        await repository.delete(resource.draft_data_id)
    await database.resource.delete(resource.id)
