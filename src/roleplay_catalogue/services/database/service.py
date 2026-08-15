from pymongo import AsyncMongoClient

from .user import UserRepository


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

    async def close(self) -> None:
        await self._client.close()
