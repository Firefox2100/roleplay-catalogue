from pymongo import AsyncMongoClient

from roleplay_catalogue.models import ImageDataDocument
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCharacterDataDocument,
    SillyTavernLorebookDataDocument,
)
from .user import UserRepository
from .activation_token import ActivationTokenRepository
from .resource import ResourceRepository
from .resource_data import ResourceDataRepository
from .resource_version import ResourceVersionRepository


class DatabaseService:
    def __init__(self,
                 client: AsyncMongoClient,
                 database_name: str,
                 ):
        self._client = client
        self._database_name = database_name

        self._db = client[database_name]

    @property
    def user(self) -> UserRepository:
        return UserRepository(self._db)

    @property
    def activation_token(self) -> ActivationTokenRepository:
        return ActivationTokenRepository(self._db)

    @property
    def resource(self) -> ResourceRepository:
        return ResourceRepository(self._db)

    @property
    def resource_version(self) -> ResourceVersionRepository:
        return ResourceVersionRepository(self._db)

    @property
    def silly_tavern_character_data(
            self,
    ) -> ResourceDataRepository[SillyTavernCharacterDataDocument]:
        return ResourceDataRepository(
            self._db,
            'sillytavern_character_data',
            SillyTavernCharacterDataDocument,
        )

    @property
    def silly_tavern_lorebook_data(self) -> ResourceDataRepository[SillyTavernLorebookDataDocument]:
        return ResourceDataRepository(
            self._db,
            'sillytavern_lorebook_data',
            SillyTavernLorebookDataDocument,
        )

    @property
    def image_data(self) -> ResourceDataRepository[ImageDataDocument]:
        return ResourceDataRepository(self._db, 'image_data', ImageDataDocument)

    async def initialize(self) -> None:
        await self._db['users'].create_index('id', unique=True)
        await self._db['users'].create_index('username', unique=True)
        await self._db['activation_tokens'].create_index('username', unique=True)
        await self._db['activation_tokens'].create_index('expiresAt', expireAfterSeconds=0)
        await self._db['resources'].create_index('id', unique=True)
        await self._db['resources'].create_index([('authorId', 1), ('updatedAt', -1)])
        await self._db['resources'].create_index([('metadata.visibility', 1), ('updatedAt', -1)])
        await self._db['resources'].create_index([('resourceType', 1), ('updatedAt', -1)])
        await self._db['resources'].create_index('metadata.tags')
        await self._db['resource_versions'].create_index('id', unique=True)
        await self._db['resource_versions'].create_index(
            [('resourceId', 1), ('versionNumber', -1)],
            unique=True,
        )
        await self._db['resource_versions'].create_index('coverImageResourceId')

        for collection_name in (
                'sillytavern_character_data',
                'sillytavern_lorebook_data',
                'image_data',
        ):
            await self._db[collection_name].create_index('id', unique=True)
            await self._db[collection_name].create_index('resourceId')
        await self._db['image_data'].create_index('sha256')

    async def close(self) -> None:
        await self._client.close()
