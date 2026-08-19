from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ConfigDict, Field, model_validator

from roleplay_catalogue.models.common import CommonModel
from roleplay_catalogue.misc import ResourceLanguage, ResourceType, ResourceVisibility


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResourceMetadata(CommonModel):
    model_config = ConfigDict(
        frozen=True,
        serialize_by_alias=True,
    )

    name: str = Field(
        ...,
        min_length=1,
        description='Display name of the resource',
    )
    description: str = Field(
        '',
        description='Description of the resource',
    )
    language: ResourceLanguage = Field(
        ResourceLanguage.ENGLISH_UK,
        description='Primary language of the resource content',
    )
    visibility: ResourceVisibility = Field(
        ResourceVisibility.PRIVATE,
        description='Who may discover and read the resource',
    )
    tags: tuple[str, ...] = Field(
        default_factory=tuple,
        description='Search and discovery tags',
    )


class ResourceVersionReference(CommonModel):
    model_config = ConfigDict(
        frozen=True,
        serialize_by_alias=True,
    )

    resource_id: str = Field(
        ...,
        description='Canonical resource ID',
        alias='resourceId',
    )
    version_id: str = Field(
        ...,
        description='Exact immutable version ID',
        alias='versionId',
    )
    instance: str | None = Field(
        None,
        description='Canonical base URL of the originating federated instance',
    )


class LorebookReference(CommonModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True)

    resource_id: str = Field(..., alias='resourceId')
    version_id: str | None = Field(
        None, alias='versionId',
        description='Exact release ID, or null when following an owned lorebook draft',
    )
    name: str | None = Field(None, description='Lorebook name captured for release display')
    author: str | None = Field(None, description='Lorebook author username captured for attribution')
    version: str | None = Field(None, description='Lorebook release label captured for display')


class Resource(CommonModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='Canonical resource ID',
    )
    resource_type: ResourceType = Field(
        ...,
        description='Namespaced type used to locate the type-specific data collection',
        alias='resourceType',
    )
    author_id: str = Field(
        ...,
        description='User who owns and authors the mutable resource',
        alias='authorId',
    )
    co_author_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            'Users granted editing permission by the author. Co-authors may view and edit the '
            'draft, including linking it as a draft from another resource, but may not publish a '
            'release or delete the resource.'
        ),
        alias='coAuthorIds',
    )
    metadata: ResourceMetadata = Field(
        ...,
        description='Current mutable metadata',
    )
    draft_data_id: str | None = Field(
        None,
        description='Current payload in the type-specific collection, if one exists',
        alias='draftDataId',
    )
    cover_image_resource_id: str | None = Field(
        None,
        description='Immutable image resource used as the current draft cover',
        alias='coverImageResourceId',
    )
    linked_lorebooks: tuple[LorebookReference, ...] = Field(
        default_factory=tuple,
        description='Standalone lorebook drafts or exact releases linked to this character draft',
        alias='linkedLorebooks',
    )

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_lorebook_links(cls, value):
        if isinstance(value, dict) and 'linkedLorebooks' not in value:
            legacy = value.get('linkedLorebookResourceIds', [])
            if legacy:
                value = {**value, 'linkedLorebooks': [
                    {'resourceId': resource_id, 'versionId': None} for resource_id in legacy
                ]}
        return value
    forked_from: ResourceVersionReference | None = Field(
        None,
        description='Exact version from which this resource was forked',
        alias='forkedFrom',
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description='Time at which the canonical resource was created',
        alias='createdAt',
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description='Time at which the draft or metadata was last updated',
        alias='updatedAt',
    )


class ResourceVersion(CommonModel):
    model_config = ConfigDict(
        frozen=True,
        serialize_by_alias=True,
    )

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='Immutable version ID',
    )
    resource_id: str = Field(
        ...,
        description='Canonical resource to which this version belongs',
        alias='resourceId',
    )
    resource_type: ResourceType = Field(
        ...,
        description='Namespaced type used to locate the version payload',
        alias='resourceType',
    )
    version_number: int = Field(
        ...,
        ge=1,
        description='Monotonically increasing version number within the resource',
        alias='versionNumber',
    )
    version: str = Field(
        '1',
        min_length=1,
        max_length=100,
        description='User supplied release label, preferably a semantic version',
    )
    data_id: str = Field(
        ...,
        description='Immutable snapshot in the type-specific data collection',
        alias='dataId',
    )
    cover_image_resource_id: str | None = Field(
        None,
        description='Image resource used as the cover when this version was published',
        alias='coverImageResourceId',
    )
    linked_lorebooks: tuple[LorebookReference, ...] = Field(
        default_factory=tuple,
        description='Exact lorebook releases captured when this character release was published',
        alias='linkedLorebooks',
    )

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_lorebook_links(cls, value):
        if isinstance(value, dict) and 'linkedLorebooks' not in value:
            legacy = value.get('linkedLorebookResourceIds', [])
            if legacy:
                value = {**value, 'linkedLorebooks': [
                    {'resourceId': resource_id, 'versionId': None} for resource_id in legacy
                ]}
        return value
    metadata: ResourceMetadata = Field(
        ...,
        description='Metadata snapshot taken at publication time',
    )
    visibility: ResourceVisibility = Field(
        ResourceVisibility.PRIVATE,
        description='Mutable access level for this otherwise immutable release',
    )
    artifact_object_key: str | None = Field(None, alias='artifactObjectKey')
    artifact_content_type: str | None = Field(None, alias='artifactContentType')
    artifact_file_name: str | None = Field(None, alias='artifactFileName')
    artifact_byte_size: int | None = Field(None, ge=0, alias='artifactByteSize')
    artifact_sha256: str | None = Field(None, alias='artifactSha256')
    published_by_id: str = Field(
        ...,
        description='User who published this version',
        alias='publishedById',
    )
    previous_version_id: str | None = Field(
        None,
        description='Previous published version in this resource history',
        alias='previousVersionId',
    )
    content_diff: str | None = Field(
        None,
        description=(
            'Unified text diff of this release\'s complete content against previous_version_id, '
            'including any linked or merged resources embedded in the release (for example a '
            "character's linked lorebooks). The first release in a resource's history is diffed "
            "as if the previous release were empty, mirroring git's treatment of an initial "
            'commit. Null for resource types with no textual content, such as images.'
        ),
        alias='contentDiff',
    )
    published_at: datetime = Field(
        default_factory=utc_now,
        description='Publication time',
        alias='publishedAt',
    )


class ResourceDataDocument(CommonModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description='Type-specific payload ID',
    )
    resource_id: str = Field(
        ...,
        description='Canonical resource owning this payload',
        alias='resourceId',
    )
    resource_version_id: str | None = Field(
        None,
        description='Version using this snapshot; null denotes mutable draft data',
        alias='resourceVersionId',
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description='Payload creation time',
        alias='createdAt',
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description='Last payload update time',
        alias='updatedAt',
    )
