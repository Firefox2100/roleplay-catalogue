from roleplay_catalogue.models import (
    ImageDataDocument,
    Resource,
    ResourceVersion,
    WorldBundleData,
    WorldDataDocument,
    WorldMediaReference,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCardV3LoreBook,
    SillyTavernLorebookDataDocument,
)
from roleplay_catalogue.services.database.integrity import check_integrity


def make_resource(**overrides) -> Resource:
    defaults = {
        'resourceType': 'sillytavern/character', 'authorId': 'author-id',
        'metadata': {'name': 'Example'},
    }
    return Resource(**{**defaults, **overrides})


async def test_check_integrity_reports_nothing_for_a_consistent_database(
        database_service, mongo_database) -> None:
    assert await check_integrity(mongo_database) == []


async def test_check_integrity_finds_a_resource_with_a_missing_author(database_service) -> None:
    await database_service.resource.create(make_resource(authorId='missing-author'))

    problems = await database_service.check_integrity()

    assert any('missing author' in problem for problem in problems)


async def test_check_integrity_finds_a_version_with_a_missing_resource_or_publisher(
        database_service) -> None:
    await database_service.resource_version.create(ResourceVersion(
        resourceId='missing-resource', resourceType='sillytavern/lorebook', versionNumber=1,
        dataId='data-id', metadata={'name': 'Lore'}, publishedById='missing-publisher',
    ))

    problems = await database_service.check_integrity()

    assert any('missing resource' in problem for problem in problems)
    assert any('missing publisher' in problem for problem in problems)


async def test_check_integrity_finds_a_snapshot_with_a_missing_version(database_service) -> None:
    resource = await database_service.resource.create(make_resource(
        resourceType='sillytavern/lorebook',
    ))
    await database_service.silly_tavern_lorebook_data.create(SillyTavernLorebookDataDocument(
        resourceId=resource.id, resourceVersionId='missing-version',
        data=SillyTavernCardV3LoreBook(),
    ))

    problems = await database_service.check_integrity()

    assert any('lorebook snapshots' in problem and 'missing version' in problem for problem in problems)


async def test_check_integrity_finds_world_media_referencing_a_missing_image(database_service) -> None:
    world = await database_service.resource.create(make_resource(
        resourceType='world-simulation-engine/world',
    ))
    await database_service.world_data.create(WorldDataDocument(
        resourceId=world.id,
        data=WorldBundleData(
            world={
                'id': world.id, 'name': 'World', 'starting_time': '2026-01-01T00:00:00Z',
                'language': 'en',
            },
            media=[WorldMediaReference(
                mediaId='cover', imageResourceId='missing-image', record={'id': 'cover'},
            )],
        ),
    ))

    problems = await database_service.check_integrity()

    assert any('world media links with a missing image' in problem for problem in problems)


async def test_check_integrity_finds_a_character_link_to_a_missing_lorebook_resource(
        database_service) -> None:
    await database_service.resource.create(make_resource(
        linkedLorebooks=[{'resourceId': 'missing-lorebook', 'versionId': None}],
    ))

    problems = await database_service.check_integrity()

    assert any(
        'character lorebook links with a missing lorebook' in problem for problem in problems
    )


async def test_check_integrity_finds_a_draft_link_to_a_missing_lorebook_release(
        database_service) -> None:
    lorebook = await database_service.resource.create(make_resource(
        resourceType='sillytavern/lorebook',
    ))
    await database_service.resource.create(make_resource(
        linkedLorebooks=[{'resourceId': lorebook.id, 'versionId': 'missing-version'}],
    ))

    problems = await database_service.check_integrity()

    assert any(
        'character draft lorebook release links' in problem and 'missing version' in problem
        for problem in problems
    )


async def test_check_integrity_finds_a_release_link_to_a_missing_lorebook_release(
        database_service) -> None:
    lorebook = await database_service.resource.create(make_resource(
        resourceType='sillytavern/lorebook',
    ))
    character = await database_service.resource.create(make_resource())
    await database_service.resource_version.create(ResourceVersion(
        resourceId=character.id, resourceType='sillytavern/character', versionNumber=1,
        dataId='data-id', metadata={'name': 'Example'}, publishedById=character.author_id,
        linkedLorebooks=[{'resourceId': lorebook.id, 'versionId': 'missing-version'}],
    ))

    problems = await database_service.check_integrity()

    assert any(
        'character release lorebook links' in problem and 'missing version' in problem
        for problem in problems
    )


async def test_check_integrity_finds_image_data_with_a_missing_resource(database_service) -> None:
    await database_service.image_data.create(ImageDataDocument(
        resourceId='missing-resource', objectKey='images/x.png', contentType='image/png',
        byteSize=1, sha256='a' * 64, width=1, height=1,
    ))

    problems = await database_service.check_integrity()

    assert any('image documents with a missing resource' in problem for problem in problems)
