from collections.abc import AsyncIterator
from asyncio import sleep
from typing import Any
from urllib.parse import quote


class StorageService:
    def __init__(self,
                 client: Any,
                 bucket: str,
                 signed_url_expiry: int = 120,
                 ):
        self._client = client
        self._bucket = bucket
        self._signed_url_expiry = signed_url_expiry

    @property
    def signed_url_expiry(self) -> int:
        return self._signed_url_expiry

    async def create_signed_download_url(self,
                                         key: str,
                                         file_name: str,
                                         ) -> str:
        return await self._client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self._bucket,
                'Key': key,
                'ResponseContentDisposition': (
                    f"attachment; filename*=UTF-8''{quote(file_name, safe='')}"
                ),
            },
            ExpiresIn=self._signed_url_expiry,
        )

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

    async def wait_until_available(self,
                                   key: str,
                                   attempts: int = 8,
                                   delay: float = 0.25,
                                   ) -> None:
        last_error = None
        for attempt in range(attempts):
            try:
                await self._client.head_object(Bucket=self._bucket, Key=key)
                return
            except Exception as error:
                last_error = error
                if attempt + 1 < attempts:
                    await sleep(delay * (attempt + 1))
        if last_error:
            raise last_error

    async def fetch(self,
                    key: str,
                    chunk_size: int = 64 * 1024,
                    ) -> AsyncIterator[bytes]:
        response = await self._client.get_object(Bucket=self._bucket, Key=key)
        body = response['Body']
        async with body:
            while chunk := await body.read(chunk_size):
                yield chunk
