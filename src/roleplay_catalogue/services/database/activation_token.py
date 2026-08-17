from pymongo.asynchronous.database import AsyncDatabase

from roleplay_catalogue.models import ActivationToken
from .transaction import current_session


class ActivationTokenRepository:
    def __init__(self,
                 db: AsyncDatabase,
                 ):
        self._collection = db['activation_tokens']

    async def create(self, activation_token: ActivationToken) -> ActivationToken:
        await self._collection.replace_one(
            {'username': activation_token.username},
            activation_token.model_dump(mode='python', by_alias=True),
            upsert=True,
            session=current_session(),
        )
        return activation_token

    async def get(self, username: str) -> ActivationToken | None:
        document = await self._collection.find_one(
            {'username': username}, {'_id': 0}, session=current_session(),
        )
        return ActivationToken.model_validate(document) if document else None

    async def delete(self, username: str) -> bool:
        result = await self._collection.delete_one({'username': username}, session=current_session())
        return result.deleted_count == 1
