from typing import Any

from fastapi import HTTPException, status

from roleplay_catalogue.models import Resource, ResourceType, ResourceVersion, ResourceVisibility, User
from roleplay_catalogue.services import DatabaseService


def can_read_resource(resource: Resource,
                      user: User | None,
                      ) -> bool:
    if resource.metadata.visibility == ResourceVisibility.PUBLIC:
        return True
    if not user:
        return False
    return (resource.metadata.visibility == ResourceVisibility.AUTHENTICATED or
            resource.author_id == user.id)


async def get_readable_resource(database: DatabaseService,
                                resource_id: str,
                                user: User | None,
                                ) -> Resource:
    resource = await database.resource.get(resource_id)
    if not resource or not can_read_resource(resource, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
    return resource


async def get_owned_resource(database: DatabaseService,
                             resource_id: str,
                             user: User,
                             expected_type: ResourceType | None = None,
                             ) -> Resource:
    resource = await database.resource.get(resource_id)
    if not resource or resource.author_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource not found')
    if expected_type is not None and resource.resource_type != expected_type:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Resource type does not match this endpoint')
    return resource


async def get_readable_version(database: DatabaseService,
                               version_id: str,
                               user: User | None,
                               ) -> ResourceVersion:
    version = await database.resource_version.get(version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    resource = await database.resource.get(version.resource_id)
    if not resource:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    if user and resource.author_id == user.id:
        return version
    if version.visibility == ResourceVisibility.PRIVATE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    if version.visibility == ResourceVisibility.AUTHENTICATED and not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Resource version not found')
    return version


def get_data_repository(database: DatabaseService,
                        resource_type: ResourceType,
                        ) -> Any:
    attribute = {
        ResourceType.SILLY_TAVERN_CHARACTER: 'silly_tavern_character_data',
        ResourceType.SILLY_TAVERN_LOREBOOK: 'silly_tavern_lorebook_data',
        ResourceType.SILLY_TAVERN_PRESET: 'silly_tavern_preset_data',
        ResourceType.IMAGE: 'image_data',
        ResourceType.WORLD_SIMULATION_WORLD: 'world_data',
    }[resource_type]
    return getattr(database, attribute)
