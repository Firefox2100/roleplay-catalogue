from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import User


class UserRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._db = db
        self._collection = db['users']

    async def get(self, user_id: str) -> User | None:
        document = await self._collection.find_one({'id': user_id}, {'_id': 0})

        if document:
            return User.model_validate(document)

        return None

    async def get_by_username(self, username: str) -> User | None:
        document = await self._collection.find_one({'username': username}, {'_id': 0})

        if document:
            return User.model_validate(document)

        return None

    async def list(self) -> list[User]:
        cursor = self._collection.find({}, {'_id': 0})

        return [User.model_validate(doc) async for doc in cursor]
