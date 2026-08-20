"""Lifecycle-managed Redis service."""

from redis.asyncio import Redis

from roleplay_catalogue.models import ActivationToken, PasswordResetToken

from .repository import ExpiringTokenRepository
from .resource_metrics import ResourceMetricsRepository


class CacheService:
    """Application cache and ephemeral state, backed by an injected async client."""

    def __init__(self, client: Redis, key_prefix: str = 'roleplay-catalogue'):
        self._client = client
        self._key_prefix = key_prefix.rstrip(':')

    @property
    def activation_token(self) -> ExpiringTokenRepository[ActivationToken]:
        """Return the activation-token repository."""
        return ExpiringTokenRepository(
            self._client, f'{self._key_prefix}:activation-token', ActivationToken, 'username',
        )

    @property
    def password_reset_token(self) -> ExpiringTokenRepository[PasswordResetToken]:
        """Return the password-reset-token repository."""
        return ExpiringTokenRepository(
            self._client, f'{self._key_prefix}:password-reset-token', PasswordResetToken, 'user_id',
        )

    @property
    def resource_metrics(self) -> ResourceMetricsRepository:
        """Return the persistent resource-metrics repository."""
        return ResourceMetricsRepository(
            self._client, f'{self._key_prefix}:resource-metrics',
        )

    async def initialize(self) -> None:
        """Verify Redis connectivity before serving requests."""
        await self._client.ping()

    async def close(self) -> None:
        """Close the injected Redis client's connection pool."""
        await self._client.aclose()
