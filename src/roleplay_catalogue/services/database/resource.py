from re import escape

from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import Resource, ResourceType, ResourceVisibility


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
                           resource_type: ResourceType | None = None,
                           tags: list[str] | None = None,
                           author_id: str | None = None,
                           published_resource_ids: list[str] | None = None,
                           ) -> list[Resource]:
        visibility = [ResourceVisibility.PUBLIC.value]
        if user_id:
            visibility.append(ResourceVisibility.AUTHENTICATED.value)
            visibility_query = {
                '$or': [
                    {'metadata.visibility': {'$in': visibility}},
                    {'authorId': user_id},
                ]
            }
        else:
            visibility_query = {'metadata.visibility': ResourceVisibility.PUBLIC.value}

        filters = [visibility_query]
        if resource_type:
            filters.append({'resourceType': resource_type.value})
        if tags:
            filters.append({'metadata.tags': {'$all': tags}})
        if author_id:
            filters.append({'authorId': author_id})
        if published_resource_ids is not None:
            filters.append({'id': {'$in': published_resource_ids}})
        query = filters[0] if len(filters) == 1 else {'$and': filters}

        cursor = (
            self._collection.find(query, {'_id': 0})
            .sort('updatedAt', -1)
            .skip(offset)
            .limit(limit)
        )
        return [Resource.model_validate(document) async for document in cursor]

    async def suggest_tags(self,
                           user_id: str | None,
                           search: str,
                           limit: int = 10,
                           ) -> list[str]:
        visibility = [ResourceVisibility.PUBLIC.value]
        if user_id:
            visibility.append(ResourceVisibility.AUTHENTICATED.value)
            visibility_query = {'$or': [
                {'metadata.visibility': {'$in': visibility}},
                {'authorId': user_id},
            ]}
        else:
            visibility_query = {'metadata.visibility': ResourceVisibility.PUBLIC.value}

        cursor = self._collection.aggregate([
            {'$match': visibility_query},
            {'$unwind': '$metadata.tags'},
            {'$match': {'metadata.tags': {'$regex': escape(search), '$options': 'i'}}},
            {'$group': {
                '_id': {'$toLower': '$metadata.tags'},
                'tag': {'$first': '$metadata.tags'},
                'uses': {'$sum': 1},
            }},
            {'$sort': {'uses': -1, 'tag': 1}},
            {'$limit': limit},
        ])
        return [document['tag'] async for document in cursor]

    async def update(self, resource: Resource) -> Resource:
        await self._collection.replace_one(
            {'id': resource.id},
            resource.model_dump(mode='json', by_alias=True),
        )
        return resource

    async def delete(self, resource_id: str) -> bool:
        result = await self._collection.delete_one({'id': resource_id})
        return result.deleted_count == 1

    async def clear_cover_reference(self, image_resource_id: str) -> None:
        await self._collection.update_many(
            {'coverImageResourceId': image_resource_id},
            {'$set': {'coverImageResourceId': None}},
        )
