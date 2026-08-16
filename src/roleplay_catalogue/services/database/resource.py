from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import Resource, ResourceVisibility


class ResourceRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._collection = db['resources']

    async def create(self, resource: Resource) -> Resource:
        await self._collection.insert_one(resource.model_dump(mode='json', by_alias=True))
        return resource

    async def get(self, resource_id: str) -> Resource | None:
        document = await self._collection.find_one({'id': resource_id}, {'_id': 0})
        return Resource.model_validate(document) if document else None

    async def list_visible(self,
                           user_id: str | None,
                           offset: int = 0,
                           limit: int = 50,
                           ) -> list[Resource]:
        visibility = [ResourceVisibility.PUBLIC.value]
        if user_id:
            visibility.append(ResourceVisibility.AUTHENTICATED.value)
            query = {
                '$or': [
                    {'metadata.visibility': {'$in': visibility}},
                    {'authorId': user_id},
                ]
            }
        else:
            query = {'metadata.visibility': ResourceVisibility.PUBLIC.value}

        cursor = self._collection.find(query, {'_id': 0}).skip(offset).limit(limit)
        return [Resource.model_validate(document) async for document in cursor]

    async def update(self, resource: Resource) -> Resource:
        await self._collection.replace_one(
            {'id': resource.id},
            resource.model_dump(mode='json', by_alias=True),
        )
        return resource

    async def delete(self, resource_id: str) -> bool:
        result = await self._collection.delete_one({'id': resource_id})
        return result.deleted_count == 1
