from pymongo import AsyncMongoClient

from roleplay_catalogue.models import ImageDataDocument, WorldDataDocument
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCharacterDataDocument,
    SillyTavernLorebookDataDocument,
)
from .user import UserRepository
from .activation_token import ActivationTokenRepository
from .resource import ResourceRepository
from .resource_data import ResourceDataRepository
from .resource_version import ResourceVersionRepository
from .password_reset_token import PasswordResetTokenRepository
from .api_key import ApiKeyRepository
from .indexes import ensure_indexes
from .integrity import check_integrity
from .transaction import CURRENT_SESSION


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
    def password_reset_token(self) -> PasswordResetTokenRepository:
        return PasswordResetTokenRepository(self._db)

    @property
    def api_key(self) -> ApiKeyRepository:
        return ApiKeyRepository(self._db)

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

    @property
    def world_data(self) -> ResourceDataRepository[WorldDataDocument]:
        return ResourceDataRepository(self._db, 'world_data', WorldDataDocument)

    async def initialize(self) -> None:
        await ensure_indexes(self._db)

    async def check_integrity(self) -> list[str]:
        return await check_integrity(self._db)

    async def transaction(self, operation):
        async with self._client.start_session() as session:
            async def run_in_context(active_session):
                token = CURRENT_SESSION.set(active_session)
                try:
                    return await operation()
                finally:
                    CURRENT_SESSION.reset(token)

            return await session.with_transaction(run_in_context)

    async def close(self) -> None:
        await self._client.close()
