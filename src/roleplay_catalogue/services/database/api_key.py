from datetime import datetime

from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import ApiKey
from .transaction import current_session


class ApiKeyRepository:
    def __init__(self, db: AsyncDatabase):
        self._collection = db['api_keys']

    async def create(self, api_key: ApiKey) -> ApiKey:
        await self._collection.insert_one(
            api_key.model_dump(mode='python', by_alias=True), session=current_session(),
        )
        return api_key

    async def get(self, key_id: str) -> ApiKey | None:
        document = await self._collection.find_one(
            {'id': key_id}, {'_id': 0}, session=current_session(),
        )
        return ApiKey.model_validate(document) if document else None

    async def list_for_user(self, user_id: str) -> list[ApiKey]:
        cursor = self._collection.find(
            {'userId': user_id}, {'_id': 0}, session=current_session(),
        ).sort('createdAt', -1)
        return [ApiKey.model_validate(document) async for document in cursor]

    async def delete(self, key_id: str, user_id: str | None = None) -> bool:
        query = {'id': key_id}
        if user_id is not None:
            query['userId'] = user_id
        result = await self._collection.delete_one(query, session=current_session())
        return result.deleted_count == 1

    async def delete_for_user(self, user_id: str) -> int:
        result = await self._collection.delete_many(
            {'userId': user_id}, session=current_session(),
        )
        return result.deleted_count

    async def delete_expired(self, now: datetime) -> int:
        result = await self._collection.delete_many(
            {'expiresAt': {'$ne': None, '$lte': now}}, session=current_session(),
        )
        return result.deleted_count
