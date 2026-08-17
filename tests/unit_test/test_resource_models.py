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


def test_character_draft_and_version_can_reference_cover_image_resource() -> None:
    resource = Resource(
        resourceType='sillytavern/character',
        authorId='user-id',
        metadata=ResourceMetadata(name='Character'),
        coverImageResourceId='image-resource-id',
    )
    version = ResourceVersion(
        resourceId=resource.id,
        resourceType=resource.resource_type,
        versionNumber=1,
        dataId='data-id',
        metadata=resource.metadata,
        publishedById='user-id',
        coverImageResourceId=resource.cover_image_resource_id,
    )

    assert version.cover_image_resource_id == 'image-resource-id'


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


def test_character_data_allows_embedded_lorebook() -> None:
    document = SillyTavernCharacterDataDocument(
        resourceId='resource-id',
        data=SillyTavernCharacterData(
            name='Example character',
            character_book={
                'name': 'Character-specific lore',
                'entries': [{
                    'keys': ['example'],
                    'content': 'Embedded lore',
                    'enabled': True,
                    'insertion_order': 0,
                    'use_regex': False,
                    'constant': False,
                }],
            },
        ),
    )
    assert document.data.character_book.entries[0].content == 'Embedded lore'
    assert document.resource_version_id is None


def test_character_data_preserves_typed_script_extensions() -> None:
    data = SillyTavernCharacterData.model_validate({
        'name': 'Scripted character',
        'extensions': {
            'regex_scripts': [{
                'id': 'regex-id',
                'scriptName': 'Strip markers',
                'findRegex': '/<note>.*?<\\/note>/gs',
                'replaceString': '',
                'placement': [1, 2],
                'runOnEdit': True,
                'extensionSpecificOption': 'preserved',
            }],
            'tavern_helper': {
                'scripts': [{
                    'id': 'script-id',
                    'name': 'State updater',
                    'content': 'return;',
                    'data': {'entrypoint': 'message_received'},
                }],
                'variables': {'enabled': True},
            },
            'another_client': {'value': 1},
        },
    })

    payload = data.model_dump(mode='json', by_alias=True)
    assert payload['extensions']['regex_scripts'][0]['scriptName'] == 'Strip markers'
    assert payload['extensions']['regex_scripts'][0]['extensionSpecificOption'] == 'preserved'
    assert payload['extensions']['tavern_helper']['scripts'][0]['content'] == 'return;'
    assert payload['extensions']['another_client'] == {'value': 1}


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
