"""Redis repositories for ephemeral application data."""

from datetime import datetime, timezone
from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis


TokenModel = TypeVar('TokenModel', bound=BaseModel)


class ExpiringTokenRepository(Generic[TokenModel]):
    """Redis-backed storage for single-use, expiring credentials."""

    def __init__(self, client: Redis, prefix: str, model: type[TokenModel], identity: str):
        self._client = client
        self._prefix = prefix
        self._model = model
        self._identity = identity

    def _key(self, identity: str) -> str:
        return f'{self._prefix}:{identity}'

    async def create(self, token: TokenModel) -> TokenModel:
        """Store or replace a token until its model-defined expiry time."""
        expires_at = getattr(token, 'expires_at')
        ttl = max(1, ceil((expires_at - datetime.now(timezone.utc)).total_seconds()))
        await self._client.set(
            self._key(getattr(token, self._identity)),
            token.model_dump_json(by_alias=True),
            ex=ttl,
        )
        return token

    async def get(self, identity: str) -> TokenModel | None:
        """Return the token for an identity, if it has not expired."""
        value = await self._client.get(self._key(identity))
        return self._model.model_validate_json(value) if value is not None else None

    async def delete(self, identity: str) -> bool:
        """Delete an identity's token and report whether it existed."""
        return bool(await self._client.delete(self._key(identity)))
