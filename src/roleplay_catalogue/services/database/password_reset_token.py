from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import PasswordResetToken
from .transaction import current_session


class PasswordResetTokenRepository:
    def __init__(self, db: AsyncDatabase):
        self._collection = db['password_reset_tokens']

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        await self._collection.replace_one(
            {'userId': token.user_id},
            token.model_dump(mode='python', by_alias=True),
            upsert=True,
            session=current_session(),
        )
        return token

    async def get(self, user_id: str) -> PasswordResetToken | None:
        document = await self._collection.find_one(
            {'userId': user_id}, {'_id': 0}, session=current_session(),
        )
        return PasswordResetToken.model_validate(document) if document else None

    async def delete(self, user_id: str) -> bool:
        result = await self._collection.delete_one({'userId': user_id}, session=current_session())
        return result.deleted_count == 1
