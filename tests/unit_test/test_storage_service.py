from roleplay_catalogue.services import StorageService


class MemoryBody:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def read(self, size: int) -> bytes:
        chunk = self.data[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class MemoryS3Client:
    def __init__(self):
        self.objects = {}

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)

    async def get_object(self, Bucket, Key):
        return {'Body': MemoryBody(self.objects[(Bucket, Key)][0])}

    async def head_object(self, Bucket, Key):
        return {'ContentLength': len(self.objects[(Bucket, Key)][0])}

    async def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)

    async def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f'https://storage.test/{Params["Key"]}?expires={ExpiresIn}'


async def test_storage_upload_fetch_and_remove() -> None:
    client = MemoryS3Client()
    storage = StorageService(client=client, bucket='assets')

    await storage.upload('images/example.png', b'png-data', 'image/png')
    await storage.wait_until_available('images/example.png')
    chunks = [chunk async for chunk in storage.fetch('images/example.png', chunk_size=3)]

    assert b''.join(chunks) == b'png-data'
    assert client.objects[('assets', 'images/example.png')][1] == 'image/png'

    await storage.remove('images/example.png')
    assert client.objects == {}


async def test_storage_creates_expiring_signed_download_url() -> None:
    storage = StorageService(
        client=MemoryS3Client(), bucket='assets', signed_url_expiry=45,
    )

    url = await storage.create_signed_download_url('releases/card.json', 'My card.json')

    assert url == 'https://storage.test/releases/card.json?expires=45'
    assert storage.signed_url_expiry == 45
