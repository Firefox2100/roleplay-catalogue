from typing import Generic, TypeVar

from pydantic import BaseModel
from pymongo.asynchronous.database import AsyncDatabase


DataDocument = TypeVar('DataDocument', bound=BaseModel)


class ResourceDataRepository(Generic[DataDocument]):
    def __init__(self,
                 db: AsyncDatabase,
                 collection_name: str,
                 model: type[DataDocument],
                 ):
        self._collection = db[collection_name]
        self._model = model

    async def create(self, data: DataDocument) -> DataDocument:
        await self._collection.insert_one(data.model_dump(mode='json', by_alias=True))
        return data

    async def get(self, data_id: str) -> DataDocument | None:
        document = await self._collection.find_one({'id': data_id}, {'_id': 0})
        return self._model.model_validate(document) if document else None

    async def list_for_resource(self, resource_id: str) -> list[DataDocument]:
        cursor = self._collection.find({'resourceId': resource_id}, {'_id': 0})
        return [self._model.model_validate(document) async for document in cursor]

    async def list_by_sha256(self, digest: str) -> list[DataDocument]:
        cursor = self._collection.find({'sha256': digest}, {'_id': 0})
        return [self._model.model_validate(document) async for document in cursor]

    async def update(self, data: DataDocument) -> DataDocument:
        await self._collection.replace_one(
            {'id': getattr(data, 'id')},
            data.model_dump(mode='json', by_alias=True),
        )
        return data

    async def delete(self, data_id: str) -> bool:
        result = await self._collection.delete_one({'id': data_id})
        return result.deleted_count == 1
