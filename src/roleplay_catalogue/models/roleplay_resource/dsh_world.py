"""Stored metadata for lossless DeepSeek Harness agentic-roleplay world ZIPs."""

from pydantic import ConfigDict, Field

from roleplay_catalogue.models.common import CommonModel
from .resource import ResourceDataDocument


class DshWorldFile(CommonModel):
    """One file in the uploaded world folder, indexed for release diffs."""
    model_config = ConfigDict(frozen=True, serialize_by_alias=True)

    path: str
    byte_size: int = Field(..., ge=0, alias='byteSize')
    sha256: str


class DshWorldData(CommonModel):
    """An indexed, lossless DeepSeek Harness agentic-roleplay world folder."""

    model_config = ConfigDict(extra='forbid', frozen=True, serialize_by_alias=True)

    world_id: str | None = Field(None, alias='worldId')
    world_name: str = Field(..., min_length=1, alias='worldName')
    world_version: str | None = Field(None, alias='worldVersion')
    author_name: str | None = Field(None, alias='authorName')
    description: str = ''
    tags: tuple[str, ...] = ()
    folder_name: str = Field(..., alias='folderName')
    object_key: str = Field(..., alias='objectKey')
    byte_size: int = Field(..., ge=0, alias='byteSize')
    sha256: str
    files: tuple[DshWorldFile, ...]


class DshWorldDataDocument(ResourceDataDocument):
    """Mutable draft or immutable release snapshot for an uploaded world."""
    data: DshWorldData
