from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import ConfigDict, Field

from roleplay_catalogue.models.common import CommonModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResourceType(StrEnum):
    SILLY_TAVERN_CHARACTER = 'sillytavern/character'
    SILLY_TAVERN_LOREBOOK = 'sillytavern/lorebook'
    IMAGE = 'core/image'


class ResourceVisibility(StrEnum):
    PUBLIC = 'public'
    AUTHENTICATED = 'authenticated'
    PRIVATE = 'private'


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
    metadata: ResourceMetadata = Field(
        ...,
        description='Metadata snapshot taken at publication time',
    )
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
