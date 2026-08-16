from pydantic import ConfigDict, Field

from roleplay_catalogue.models.common import CommonModel
from .resource import ResourceDataDocument


class ImageData(CommonModel):
    object_key: str = Field(
        ...,
        description='Provider-independent key in the configured object storage',
        alias='objectKey',
    )
    content_type: str = Field(
        ...,
        description='IANA media type of the image',
        alias='contentType',
    )
    byte_size: int = Field(
        ...,
        ge=0,
        description='Object size in bytes',
        alias='byteSize',
    )
    sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r'^[0-9a-f]{64}$',
        description='Lowercase SHA-256 digest of the stored object',
    )
    width: int = Field(
        ...,
        gt=0,
        description='Image width in pixels',
    )
    height: int = Field(
        ...,
        gt=0,
        description='Image height in pixels',
    )


class ImageDataDocument(ResourceDataDocument, ImageData):
    model_config = ConfigDict(
        frozen=True,
        serialize_by_alias=True,
    )
