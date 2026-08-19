import httpx
import pytest


async def test_upload_fetch_and_remove_round_trip(storage_service) -> None:
    await storage_service.upload('images/example.png', b'png-bytes', 'image/png')

    chunks = [chunk async for chunk in storage_service.fetch('images/example.png')]
    assert b''.join(chunks) == b'png-bytes'

    await storage_service.remove('images/example.png')
    with pytest.raises(Exception):
        async for _ in storage_service.fetch('images/example.png'):
            pass


async def test_wait_until_available_succeeds_once_the_object_exists(storage_service) -> None:
    await storage_service.upload('images/ready.png', b'data', 'image/png')

    await storage_service.wait_until_available('images/ready.png')


async def test_wait_until_available_raises_for_a_key_that_never_appears(storage_service) -> None:
    with pytest.raises(Exception):
        await storage_service.wait_until_available('images/missing.png', attempts=2, delay=0.01)


async def test_signed_download_url_actually_downloads_the_object(storage_service) -> None:
    await storage_service.upload('releases/character.json', b'{"name": "Example"}', 'application/json')

    url = await storage_service.create_signed_download_url(
        'releases/character.json', 'Example Character.json',
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    assert response.status_code == 200
    assert response.content == b'{"name": "Example"}'
    assert "Example%20Character.json" in response.headers['content-disposition']
