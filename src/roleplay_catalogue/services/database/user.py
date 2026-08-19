from __future__ import annotations

from datetime import datetime

from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.misc import UserStatus
from roleplay_catalogue.models import User
from .transaction import current_session


class UserRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._db = db
        self._collection = db['users']

    async def get(self, user_id: str) -> User | None:
        document = await self._collection.find_one(
            {'id': user_id}, {'_id': 0}, session=current_session(),
        )

        if document:
            return User.model_validate(document)

        return None

    async def get_by_username(self, username: str) -> User | None:
        document = await self._collection.find_one(
            {'username': username}, {'_id': 0}, session=current_session(),
        )

        if document:
            return User.model_validate(document)

        return None

    async def get_by_email(self, email: str) -> User | None:
        document = await self._collection.find_one(
            {'email': email}, {'_id': 0}, session=current_session(),
        )
        return User.model_validate(document) if document else None

    async def get_many(self, user_ids: set[str]) -> dict[str, User]:
        cursor = self._collection.find(
            {'id': {'$in': list(user_ids)}}, {'_id': 0}, session=current_session(),
        )
        users = [User.model_validate(document) async for document in cursor]
        return {user.id: user for user in users}

    async def create(self, user: User) -> User:
        await self._collection.insert_one(
            user.model_dump(mode='python', by_alias=True), session=current_session(),
        )
        return user

    async def has_any(self) -> bool:
        return await self._collection.find_one(
            {}, {'_id': 1}, session=current_session(),
        ) is not None

    async def update(self, user: User) -> User:
        await self._collection.replace_one(
            {'id': user.id},
            user.model_dump(mode='python', by_alias=True),
            session=current_session(),
        )
        return user

    async def delete(self, user_id: str) -> bool:
        result = await self._collection.delete_one({'id': user_id}, session=current_session())
        return result.deleted_count == 1

    async def list(self) -> list[User]:
        cursor = self._collection.find({}, {'_id': 0}, session=current_session())

        return [User.model_validate(doc) async for doc in cursor]

    async def list_pending_before(self, cutoff: datetime) -> list[User]:
        cursor = self._collection.find(
            {'status': UserStatus.PENDING_ACTIVATION.value, 'createdAt': {'$lte': cutoff}},
            {'_id': 0},
            session=current_session(),
        )
        return [User.model_validate(document) async for document in cursor]
