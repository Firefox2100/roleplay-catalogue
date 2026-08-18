from datetime import datetime, timedelta, timezone

from roleplay_catalogue.misc import ResourceType
from roleplay_catalogue.models import User

from .database import DatabaseService
from .storage import StorageService


class AccountService:
    def __init__(self, database: DatabaseService, storage: StorageService,
                 pending_account_retention: int):
        self._database = database
        self._storage = storage
        self._pending_account_retention = pending_account_retention

    def _data_repository(self, resource_type: ResourceType):
        attribute = {
            ResourceType.SILLY_TAVERN_CHARACTER: 'silly_tavern_character_data',
            ResourceType.SILLY_TAVERN_LOREBOOK: 'silly_tavern_lorebook_data',
            ResourceType.IMAGE: 'image_data',
            ResourceType.WORLD_SIMULATION_WORLD: 'world_data',
        }[resource_type]
        return getattr(self._database, attribute)

    async def delete_account(self, user: User) -> None:
        resources = await self._database.resource.list_by_author(user.id)
        ordered = sorted(resources, key=lambda item: item.resource_type == ResourceType.IMAGE)
        object_keys: set[str] = set()

        for resource in ordered:
            repository = self._data_repository(resource.resource_type)
            versions = await self._database.resource_version.list_all_for_resource(resource.id)
            for version in versions:
                document = await repository.get(version.data_id)
                if resource.resource_type == ResourceType.IMAGE and document:
                    object_keys.add(document.object_key)
                if version.artifact_object_key:
                    object_keys.add(version.artifact_object_key)

        async def delete_records() -> None:
            for resource in ordered:
                repository = self._data_repository(resource.resource_type)
                versions = await self._database.resource_version.list_all_for_resource(resource.id)
                for version in versions:
                    document = await repository.get(version.data_id)
                    if document:
                        await repository.delete(document.id)
                    await self._database.resource_version.delete(version.id)

                if resource.draft_data_id:
                    await repository.delete(resource.draft_data_id)
                if resource.resource_type == ResourceType.IMAGE:
                    await self._database.resource.clear_cover_reference(resource.id)
                await self._database.resource.delete(resource.id)

            await self._database.activation_token.delete(user.username)
            await self._database.password_reset_token.delete(user.id)
            await self._database.api_key.delete_for_user(user.id)
            await self._database.user.delete(user.id)

        if hasattr(self._database, 'transaction'):
            await self._database.transaction(delete_records)
        else:
            await delete_records()

        for object_key in object_keys:
            await self._storage.remove(object_key)

    async def purge_expired_pending_accounts(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self._pending_account_retention,
        )
        users = await self._database.user.list_pending_before(cutoff)
        for user in users:
            await self.delete_account(user)
        return len(users)
