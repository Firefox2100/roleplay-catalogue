from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from roleplay_catalogue.models import ResourceType, ResourceVersion
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from .resource_utils import get_data_repository, get_owned_resource, get_readable_resource
from .utils import (
    AuthenticatedUserDependency,
    DatabaseDependency,
    OptionalAuthenticatedUserDependency,
)


resource_version_router = APIRouter(
    prefix='/versions',
    tags=['Resource Versions'],
)


@resource_version_router.post(
    '/{resource_id}',
    response_model=ResourceVersion,
    status_code=status.HTTP_201_CREATED,
)
async def publish_resource(resource_id: str,
                           database: DatabaseDependency,
                           user: AuthenticatedUserDependency,
                           ) -> ResourceVersion:
    resource = await get_owned_resource(database, resource_id, user)
    if not resource.draft_data_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource has no draft data')

    repository = get_data_repository(database, resource.resource_type)
    draft = await repository.get(resource.draft_data_id)
    if not draft or draft.resource_version_id:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource draft data is invalid')

    latest = await database.resource_version.get_latest(resource.id)
    version_id = str(uuid4())
    snapshot_data = draft.data
    if resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER:
        author = await database.user.get(resource.author_id)
        if not author:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Resource author no longer exists')
        snapshot_data = draft.data.model_copy(update={
            'description': resource.metadata.description,
            'tags': list(resource.metadata.tags),
            'creator': author.username,
        })
    snapshot = draft.model_copy(update={
        'id': str(uuid4()),
        'resource_version_id': version_id,
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'data': snapshot_data,
    })
    version = ResourceVersion(
        id=version_id,
        resourceId=resource.id,
        resourceType=resource.resource_type,
        versionNumber=latest.version_number + 1 if latest else 1,
        dataId=snapshot.id,
        coverImageResourceId=resource.cover_image_resource_id,
        metadata=resource.metadata,
        publishedById=user.id,
        previousVersionId=latest.id if latest else None,
    )

    await repository.create(snapshot)
    try:
        return await database.resource_version.create(version)
    except Exception:
        await repository.delete(snapshot.id)
        raise


@resource_version_router.get(
    '/resource/{resource_id}',
    response_model=list[ResourceVersion],
)
async def list_resource_versions(resource_id: str,
                                 database: DatabaseDependency,
                                 user: OptionalAuthenticatedUserDependency,
                                 offset: int = Query(0, ge=0),
                                 limit: int = Query(50, ge=1, le=100),
                                 ) -> list[ResourceVersion]:
    await get_readable_resource(database, resource_id, user)
    return await database.resource_version.list_for_resource(resource_id, offset, limit)


@resource_version_router.get('/{version_id}', response_model=ResourceVersion)
async def get_resource_version(version_id: str,
                               database: DatabaseDependency,
                               user: OptionalAuthenticatedUserDependency,
                               ) -> ResourceVersion:
    version = await database.resource_version.get(version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    await get_readable_resource(database, version.resource_id, user)
    return version
