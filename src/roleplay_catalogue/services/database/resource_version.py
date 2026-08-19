from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import ResourceVersion
from .transaction import current_session


class ResourceVersionRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._collection = db['resource_versions']

    async def create(self, version: ResourceVersion) -> ResourceVersion:
        await self._collection.insert_one(
            version.model_dump(mode='python', by_alias=True), session=current_session(),
        )
        return version

    async def update(self, version: ResourceVersion) -> ResourceVersion:
        await self._collection.replace_one(
            {'id': version.id},
            version.model_dump(mode='python', by_alias=True),
            session=current_session(),
        )
        return version

    async def get(self, version_id: str) -> ResourceVersion | None:
        document = await self._collection.find_one(
            {'id': version_id}, {'_id': 0}, session=current_session(),
        )
        return ResourceVersion.model_validate(document) if document else None

    async def list_for_resource(self,
                                resource_id: str,
                                offset: int = 0,
                                limit: int = 50,
                                ) -> list[ResourceVersion]:
        cursor = (
            self._collection
            .find({'resourceId': resource_id}, {'_id': 0}, session=current_session())
            .sort('versionNumber', -1)
            .skip(offset)
            .limit(limit)
        )
        return [ResourceVersion.model_validate(document) async for document in cursor]

    async def list_all_for_resource(self, resource_id: str) -> list[ResourceVersion]:
        cursor = self._collection.find(
            {'resourceId': resource_id}, {'_id': 0}, session=current_session(),
        )
        return [ResourceVersion.model_validate(document) async for document in cursor]

    async def get_latest(self, resource_id: str) -> ResourceVersion | None:
        document = await self._collection.find_one(
            {'resourceId': resource_id},
            {'_id': 0},
            sort=[('versionNumber', -1)],
            session=current_session(),
        )
        return ResourceVersion.model_validate(document) if document else None

    async def exists_for_resource(self, resource_id: str) -> bool:
        return await self._collection.find_one(
            {'resourceId': resource_id}, {'id': 1}, session=current_session(),
        ) is not None

    async def list_published_resource_ids(self) -> list[str]:
        return await self._collection.distinct('resourceId', session=current_session())

    async def list_by_cover(self, image_resource_id: str) -> list[ResourceVersion]:
        cursor = self._collection.find(
            {'coverImageResourceId': image_resource_id}, {'_id': 0}, session=current_session(),
        )
        return [ResourceVersion.model_validate(document) async for document in cursor]

    async def delete(self, version_id: str) -> bool:
        result = await self._collection.delete_one({'id': version_id}, session=current_session())
        return result.deleted_count == 1
