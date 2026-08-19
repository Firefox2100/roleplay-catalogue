from roleplay_catalogue.models import Resource, ResourceMetadata, ResourceVisibility, User
from roleplay_catalogue.routers.resource_utils import (
    can_read_resource,
    is_resource_editor,
    resource_editor_ids,
)


AUTHOR = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')
CO_AUTHOR = User(
    id='co-author-id', username='co-author', email='co@example.com', passwordHash='hash',
)
STRANGER = User(
    id='stranger-id', username='stranger', email='stranger@example.com', passwordHash='hash',
)


def make_resource(visibility: ResourceVisibility) -> Resource:
    return Resource(
        resourceType='sillytavern/character',
        authorId=AUTHOR.id,
        coAuthorIds=(CO_AUTHOR.id,),
        metadata=ResourceMetadata(name='Example', visibility=visibility),
    )


def test_resource_editor_ids_includes_author_and_co_authors() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert resource_editor_ids(resource) == frozenset({AUTHOR.id, CO_AUTHOR.id})


def test_is_resource_editor_true_for_author_and_co_author_only() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert is_resource_editor(resource, AUTHOR) is True
    assert is_resource_editor(resource, CO_AUTHOR) is True
    assert is_resource_editor(resource, STRANGER) is False
    assert is_resource_editor(resource, None) is False


def test_co_author_can_read_a_private_resource_like_the_author() -> None:
    resource = make_resource(ResourceVisibility.PRIVATE)

    assert can_read_resource(resource, CO_AUTHOR) is True
    assert can_read_resource(resource, STRANGER) is False
    assert can_read_resource(resource, None) is False


def test_public_and_authenticated_visibility_are_unaffected_by_co_authoring() -> None:
    public = make_resource(ResourceVisibility.PUBLIC)
    authenticated = make_resource(ResourceVisibility.AUTHENTICATED)

    assert can_read_resource(public, None) is True
    assert can_read_resource(public, STRANGER) is True
    assert can_read_resource(authenticated, None) is False
    assert can_read_resource(authenticated, STRANGER) is True
