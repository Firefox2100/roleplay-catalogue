from roleplay_catalogue.models import ImageDataDocument, WorldBundleData, WorldDataDocument, WorldMediaReference


def make_image_document(**overrides) -> ImageDataDocument:
    defaults = {
        'resourceId': 'resource-id', 'objectKey': 'images/example.png',
        'contentType': 'image/png', 'byteSize': 10, 'sha256': 'a' * 64,
        'width': 4, 'height': 4,
    }
    return ImageDataDocument(**{**defaults, **overrides})


async def test_create_get_update_and_delete_round_trip(database_service) -> None:
    document = await database_service.image_data.create(make_image_document())

    fetched = await database_service.image_data.get(document.id)
    assert fetched.id == document.id
    assert fetched.object_key == 'images/example.png'
    assert await database_service.image_data.get('missing') is None

    updated = fetched.model_copy(update={'object_key': 'images/renamed.png'})
    await database_service.image_data.update(updated)
    assert (await database_service.image_data.get(document.id)).object_key == 'images/renamed.png'

    assert await database_service.image_data.delete(document.id) is True
    assert await database_service.image_data.get(document.id) is None
    assert await database_service.image_data.delete(document.id) is False


async def test_list_for_resource_returns_every_snapshot_for_that_resource(database_service) -> None:
    draft = await database_service.image_data.create(
        make_image_document(id='draft-id'),
    )
    release = await database_service.image_data.create(
        make_image_document(id='release-id', resourceVersionId='version-id'),
    )
    await database_service.image_data.create(
        make_image_document(id='other-id', resourceId='other-resource'),
    )

    results = await database_service.image_data.list_for_resource('resource-id')

    assert {document.id for document in results} == {draft.id, release.id}


async def test_list_by_sha256_finds_content_by_digest(database_service) -> None:
    digest = 'b' * 64
    matching = await database_service.image_data.create(make_image_document(sha256=digest))
    await database_service.image_data.create(make_image_document(id='other', sha256='c' * 64))

    results = await database_service.image_data.list_by_sha256(digest)

    assert [document.id for document in results] == [matching.id]
    assert await database_service.image_data.list_by_sha256('d' * 64) == []


async def test_list_referencing_image_matches_world_media_links(database_service) -> None:
    matching = WorldDataDocument(
        resourceId='world-1',
        data=WorldBundleData(
            world={
                'id': 'world-1', 'name': 'World', 'starting_time': '2026-01-01T00:00:00Z',
                'language': 'en',
            },
            media=[WorldMediaReference(
                mediaId='cover', imageResourceId='image-resource-id', record={'id': 'cover'},
            )],
        ),
    )
    unrelated = WorldDataDocument(
        resourceId='world-2',
        data=WorldBundleData(world={
            'id': 'world-2', 'name': 'Other', 'starting_time': '2026-01-01T00:00:00Z',
            'language': 'en',
        }),
    )
    await database_service.world_data.create(matching)
    await database_service.world_data.create(unrelated)

    results = await database_service.world_data.list_referencing_image('image-resource-id')

    assert [document.resource_id for document in results] == ['world-1']
