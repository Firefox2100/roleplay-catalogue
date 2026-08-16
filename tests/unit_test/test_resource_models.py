from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from roleplay_catalogue.models import (
    ImageDataDocument,
    Resource,
    ResourceMetadata,
    ResourceType,
    ResourceVersion,
    ResourceVersionReference,
    ResourceVisibility,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCharacterData,
    SillyTavernCharacterDataDocument,
)


def test_resource_may_exist_without_draft_data() -> None:
    resource = Resource(
        resourceType='sillytavern/character',
        authorId='user-id',
        metadata=ResourceMetadata(
            name='Example character',
            visibility=ResourceVisibility.PRIVATE,
        ),
        forkedFrom=ResourceVersionReference(
            resourceId='upstream-resource-id',
            versionId='upstream-version-id',
        ),
    )

    assert resource.draft_data_id is None
    assert resource.forked_from.version_id == 'upstream-version-id'
    assert resource.created_at.tzinfo == timezone.utc


def test_resource_types_are_enumerated() -> None:
    resource = Resource(
        resourceType='sillytavern/character',
        authorId='user-id',
        metadata=ResourceMetadata(name='Character resource'),
    )

    assert resource.resource_type == ResourceType.SILLY_TAVERN_CHARACTER

    with pytest.raises(ValidationError):
        Resource(
            resourceType='another-system/custom_resource',
            authorId='user-id',
            metadata=ResourceMetadata(name='Invalid resource'),
        )


def test_published_version_is_immutable() -> None:
    version = ResourceVersion(
        resourceId='resource-id',
        resourceType='sillytavern/character',
        versionNumber=1,
        dataId='snapshot-data-id',
        metadata=ResourceMetadata(name='Published character'),
        publishedById='user-id',
        publishedAt=datetime.now(timezone.utc),
    )

    with pytest.raises(ValidationError):
        version.version_number = 2

    with pytest.raises(ValidationError):
        version.metadata.name = 'Changed name'


def test_character_data_disallows_embedded_lorebook() -> None:
    with pytest.raises(ValidationError, match='separate resources'):
        SillyTavernCharacterData(
            character_book={
                'entries': [],
            },
        )

    document = SillyTavernCharacterDataDocument(
        resourceId='resource-id',
        data=SillyTavernCharacterData(name='Example character'),
    )
    assert document.resource_version_id is None


def test_image_data_is_content_addressed_and_immutable() -> None:
    image = ImageDataDocument(
        resourceId='resource-id',
        objectKey='images/example.png',
        contentType='image/png',
        byteSize=100,
        sha256='a' * 64,
        width=128,
        height=128,
    )

    with pytest.raises(ValidationError):
        image.object_key = 'images/changed.png'
