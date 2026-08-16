from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import ResourceVersion


class ResourceVersionRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._collection = db['resource_versions']

    async def create(self, version: ResourceVersion) -> ResourceVersion:
        await self._collection.insert_one(version.model_dump(mode='json', by_alias=True))
        return version

    async def get(self, version_id: str) -> ResourceVersion | None:
        document = await self._collection.find_one({'id': version_id}, {'_id': 0})
        return ResourceVersion.model_validate(document) if document else None

    async def list_for_resource(self,
                                resource_id: str,
                                offset: int = 0,
                                limit: int = 50,
                                ) -> list[ResourceVersion]:
        cursor = (
            self._collection
            .find({'resourceId': resource_id}, {'_id': 0})
            .sort('versionNumber', -1)
            .skip(offset)
            .limit(limit)
        )
        return [ResourceVersion.model_validate(document) async for document in cursor]

    async def get_latest(self, resource_id: str) -> ResourceVersion | None:
        document = await self._collection.find_one(
            {'resourceId': resource_id},
            {'_id': 0},
            sort=[('versionNumber', -1)],
        )
        return ResourceVersion.model_validate(document) if document else None

    async def exists_for_resource(self, resource_id: str) -> bool:
        return await self._collection.find_one({'resourceId': resource_id}, {'id': 1}) is not None
