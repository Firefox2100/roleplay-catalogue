from collections.abc import AsyncIterator
from typing import Any


class StorageService:
    def __init__(self,
                 client: Any,
                 bucket: str,
                 ):
        self._client = client
        self._bucket = bucket

    async def upload(self,
                     key: str,
                     data: bytes,
                     content_type: str = 'application/octet-stream',
                     ) -> None:
        await self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def remove(self, key: str) -> None:
        await self._client.delete_object(Bucket=self._bucket, Key=key)

    async def fetch(self,
                    key: str,
                    chunk_size: int = 64 * 1024,
                    ) -> AsyncIterator[bytes]:
        response = await self._client.get_object(Bucket=self._bucket, Key=key)
        body = response['Body']
        async with body:
            while chunk := await body.read(chunk_size):
                yield chunk
