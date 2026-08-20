"""Redis-backed counters for resource engagement metrics."""

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class ResourceMetrics:
    views: int = 0
    downloads: int = 0


class ResourceMetricsRepository:
    """Persist anonymous aggregate counters using atomic Redis hash increments."""

    def __init__(self, client: Redis, prefix: str):
        self._client = client
        self._prefix = prefix

    def _key(self, resource_id: str) -> str:
        return f'{self._prefix}:{resource_id}'

    async def increment_views(self, resource_id: str) -> ResourceMetrics:
        """Increment a resource's view count and return its current metrics."""
        key = self._key(resource_id)
        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.hincrby(key, 'views', 1)
            pipeline.hget(key, 'downloads')
            views, downloads = await pipeline.execute()
        return ResourceMetrics(views=int(views), downloads=int(downloads or 0))

    async def increment_downloads(self, resource_id: str) -> int:
        """Atomically increment and return a resource's download count."""
        return int(await self._client.hincrby(self._key(resource_id), 'downloads', 1))

    async def get(self, resource_id: str) -> ResourceMetrics:
        """Return a resource's counters, defaulting missing counters to zero."""
        values = await self._client.hmget(self._key(resource_id), 'views', 'downloads')
        return ResourceMetrics(
            views=int(values[0] or 0),
            downloads=int(values[1] or 0),
        )

    async def get_many(self, resource_ids: list[str]) -> dict[str, ResourceMetrics]:
        """Fetch counters for a resource page in one Redis round trip."""
        if not resource_ids:
            return {}
        async with self._client.pipeline(transaction=False) as pipeline:
            for resource_id in resource_ids:
                pipeline.hmget(self._key(resource_id), 'views', 'downloads')
            values = await pipeline.execute()
        return {
            resource_id: ResourceMetrics(
                views=int(metrics[0] or 0), downloads=int(metrics[1] or 0),
            )
            for resource_id, metrics in zip(resource_ids, values, strict=True)
        }

    async def delete(self, resource_id: str) -> bool:
        """Remove counters when their resource is permanently deleted."""
        return bool(await self._client.delete(self._key(resource_id)))
