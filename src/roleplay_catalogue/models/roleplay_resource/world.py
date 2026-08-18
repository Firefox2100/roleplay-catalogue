from typing import Any

from pydantic import ConfigDict, Field, model_validator

from roleplay_catalogue.models.common import CommonModel
from .resource import ResourceDataDocument


WORLD_BUNDLE_SPEC = 'wse_world'
WORLD_BUNDLE_SPEC_VERSION = '1.0'

WORLD_SECTION_NAMES = (
    'locations', 'landmarks', 'characters', 'background_characters',
    'items', 'item_stacks', 'equipment', 'containers', 'turns', 'events',
    'memories', 'intents', 'entity_relationships', 'subjective_entity_claims',
    'entity_variable_sets',
)
WORLD_CONFIG_NAMES = ('chat', 'embed', 'image', 'tts')


class WorldMediaReference(CommonModel):
    model_config = ConfigDict(extra='forbid', serialize_by_alias=True)

    media_id: str = Field(..., alias='mediaId')
    image_resource_id: str | None = Field(None, alias='imageResourceId')
    record: dict[str, Any]


class WorldBundleData(CommonModel):
    """Editable representation of a World Simulation Engine v1.0 bundle.

    Entity rows deliberately retain the engine's canonical JSON shape. This keeps the
    catalogue format-compatible as that large graph model evolves independently while the
    checks below protect the stable bundle envelope and graph identifiers.
    """

    model_config = ConfigDict(extra='forbid', serialize_by_alias=True)

    spec: str = WORLD_BUNDLE_SPEC
    spec_version: str = Field(WORLD_BUNDLE_SPEC_VERSION, alias='specVersion')
    world: dict[str, Any]
    author: dict[str, Any] | None = None
    sections: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    configs: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    media: list[WorldMediaReference] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_bundle(self):
        if self.spec != WORLD_BUNDLE_SPEC or self.spec_version != WORLD_BUNDLE_SPEC_VERSION:
            raise ValueError('Only World Simulation Engine world bundle v1.0 is supported')
        required_world_fields = ('id', 'name', 'starting_time', 'language')
        missing = [field for field in required_world_fields if not self.world.get(field)]
        if missing:
            raise ValueError(f"World is missing required fields: {', '.join(missing)}")
        if self.world.get('language') not in ('en', 'zh'):
            raise ValueError('World language must be en or zh')
        unknown_sections = set(self.sections) - set(WORLD_SECTION_NAMES)
        if unknown_sections:
            raise ValueError(f'Unknown world sections: {sorted(unknown_sections)}')
        unknown_configs = set(self.configs) - set(WORLD_CONFIG_NAMES)
        if unknown_configs:
            raise ValueError(f'Unknown world config sections: {sorted(unknown_configs)}')

        ids: dict[str, str] = {str(self.world['id']): 'world'}
        for section, rows in self.sections.items():
            for index, row in enumerate(rows):
                entity_id = row.get('id')
                if not entity_id:
                    raise ValueError(f'{section}[{index}] is missing an id')
                if entity_id in ids:
                    raise ValueError(f'Duplicate graph id {entity_id!r}')
                ids[entity_id] = section
        media_ids: set[str] = set()
        for media in self.media:
            if media.media_id in media_ids:
                raise ValueError(f'Duplicate media id {media.media_id!r}')
            media_ids.add(media.media_id)
        return self


class WorldDataDocument(ResourceDataDocument):
    data: WorldBundleData
