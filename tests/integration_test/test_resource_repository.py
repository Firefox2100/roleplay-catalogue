from roleplay_catalogue.misc import ResourceType, ResourceVisibility
from roleplay_catalogue.models import Resource, ResourceMetadata


def make_resource(**overrides) -> Resource:
    defaults = {
        'resourceType': ResourceType.SILLY_TAVERN_CHARACTER,
        'authorId': 'author-id',
        'metadata': ResourceMetadata(name='Example'),
    }
    return Resource(**{**defaults, **overrides})


async def test_create_get_update_and_delete_round_trip(database_service) -> None:
    resource = await database_service.resource.create(make_resource())

    fetched = await database_service.resource.get(resource.id)
    assert fetched.id == resource.id
    assert fetched.metadata.name == 'Example'
    assert await database_service.resource.get('missing') is None

    updated = fetched.model_copy(update={
        'metadata': fetched.metadata.model_copy(update={'name': 'Renamed'}),
    })
    await database_service.resource.update(updated)
    assert (await database_service.resource.get(resource.id)).metadata.name == 'Renamed'

    assert await database_service.resource.delete(resource.id) is True
    assert await database_service.resource.get(resource.id) is None
    assert await database_service.resource.delete(resource.id) is False


async def test_list_visible_applies_visibility_rules_including_co_authors(database_service) -> None:
    public = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='Public', visibility=ResourceVisibility.PUBLIC),
    ))
    authenticated = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='Authenticated', visibility=ResourceVisibility.AUTHENTICATED),
    ))
    private = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='Private', visibility=ResourceVisibility.PRIVATE),
    ))
    co_authored = await database_service.resource.create(make_resource(
        authorId='someone-else', coAuthorIds=('reader-id',),
        metadata=ResourceMetadata(name='Co-authored', visibility=ResourceVisibility.PRIVATE),
    ))

    anonymous = await database_service.resource.list_visible(None)
    assert {resource.id for resource in anonymous} == {public.id}

    authenticated_view = await database_service.resource.list_visible('reader-id')
    assert {resource.id for resource in authenticated_view} == {
        public.id, authenticated.id, co_authored.id,
    }

    owner_view = await database_service.resource.list_visible('author-id')
    assert {resource.id for resource in owner_view} == {public.id, authenticated.id, private.id}


async def test_list_visible_filters_by_type_tags_author_and_published_ids(database_service) -> None:
    matching = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(
            name='Matching', visibility=ResourceVisibility.PUBLIC, tags=('fantasy', 'portrait'),
        ),
    ))
    await database_service.resource.create(make_resource(
        resourceType=ResourceType.SILLY_TAVERN_LOREBOOK,
        metadata=ResourceMetadata(
            name='Wrong type', visibility=ResourceVisibility.PUBLIC, tags=('fantasy', 'portrait'),
        ),
    ))
    await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='Missing tag', visibility=ResourceVisibility.PUBLIC, tags=('fantasy',)),
    ))
    other_author = await database_service.resource.create(make_resource(
        authorId='other-author',
        metadata=ResourceMetadata(name='Other author', visibility=ResourceVisibility.PUBLIC),
    ))

    by_type_and_tags = await database_service.resource.list_visible(
        None, resource_type=ResourceType.SILLY_TAVERN_CHARACTER, tags=['fantasy', 'portrait'],
    )
    assert [resource.id for resource in by_type_and_tags] == [matching.id]

    by_author = await database_service.resource.list_visible(None, author_id='other-author')
    assert [resource.id for resource in by_author] == [other_author.id]

    by_published_ids = await database_service.resource.list_visible(
        None, published_resource_ids=[matching.id],
    )
    assert [resource.id for resource in by_published_ids] == [matching.id]

    empty_published_ids = await database_service.resource.list_visible(
        None, published_resource_ids=[],
    )
    assert empty_published_ids == []


async def test_list_visible_paginates_with_offset_and_limit(database_service) -> None:
    for index in range(3):
        await database_service.resource.create(make_resource(
            metadata=ResourceMetadata(name=f'Item {index}', visibility=ResourceVisibility.PUBLIC),
        ))

    first_page = await database_service.resource.list_visible(None, limit=2)
    second_page = await database_service.resource.list_visible(None, offset=2, limit=2)

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert {resource.id for resource in first_page} | {resource.id for resource in second_page}


async def test_text_search_weighs_name_over_description_and_scores_relevance(database_service) -> None:
    name_match = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(
            name='Dragon Knight', description='A hero of the realm',
            visibility=ResourceVisibility.PUBLIC,
        ),
    ))
    description_match = await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(
            name='Village Elder', description='Fought a dragon long ago',
            visibility=ResourceVisibility.PUBLIC,
        ),
    ))
    await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='Unrelated', visibility=ResourceVisibility.PUBLIC),
    ))

    results = await database_service.resource.list_visible(None, search_string='dragon')

    assert [resource.id for resource in results] == [name_match.id, description_match.id]


async def test_suggest_tags_matches_case_insensitively_and_ranks_by_usage(database_service) -> None:
    await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(
            name='A', visibility=ResourceVisibility.PUBLIC, tags=('Portrait', 'fantasy'),
        ),
    ))
    await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='B', visibility=ResourceVisibility.PUBLIC, tags=('portrait',)),
    ))
    await database_service.resource.create(make_resource(
        metadata=ResourceMetadata(name='C', visibility=ResourceVisibility.PRIVATE, tags=('portrait-hidden',)),
    ))

    suggestions = await database_service.resource.suggest_tags(None, 'port')

    assert suggestions[0] in ('Portrait', 'portrait')
    assert 'portrait-hidden' not in suggestions


async def test_clear_cover_reference_unsets_it_on_every_matching_resource(database_service) -> None:
    first = await database_service.resource.create(make_resource(coverImageResourceId='image-1'))
    second = await database_service.resource.create(make_resource(coverImageResourceId='image-1'))
    unaffected = await database_service.resource.create(make_resource(coverImageResourceId='image-2'))

    await database_service.resource.clear_cover_reference('image-1')

    assert (await database_service.resource.get(first.id)).cover_image_resource_id is None
    assert (await database_service.resource.get(second.id)).cover_image_resource_id is None
    assert (await database_service.resource.get(unaffected.id)).cover_image_resource_id == 'image-2'


async def test_exists_lorebook_reference_reflects_linked_lorebooks(database_service) -> None:
    assert await database_service.resource.exists_lorebook_reference('lorebook-id') is False

    await database_service.resource.create(make_resource(
        linkedLorebooks=[{'resourceId': 'lorebook-id', 'versionId': None}],
    ))

    assert await database_service.resource.exists_lorebook_reference('lorebook-id') is True


async def test_remove_co_author_pulls_the_user_from_every_resource(database_service) -> None:
    resource = await database_service.resource.create(make_resource(coAuthorIds=('co-1', 'co-2')))

    await database_service.resource.remove_co_author('co-1')

    assert (await database_service.resource.get(resource.id)).co_author_ids == ('co-2',)


async def test_list_by_author_returns_only_that_authors_resources(database_service) -> None:
    mine = await database_service.resource.create(make_resource(authorId='author-a'))
    await database_service.resource.create(make_resource(authorId='author-b'))

    results = await database_service.resource.list_by_author('author-a')

    assert [resource.id for resource in results] == [mine.id]
