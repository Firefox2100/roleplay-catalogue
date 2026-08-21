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

WORLD_ENUM_FIELDS = {
    ('containers', 'state'): frozenset(('hidden', 'locked', 'unlocked', 'open')),
    ('turns', 'type'): frozenset(('user_input', 'system_response', 'system_continue')),
    ('memories', 'support_type'): frozenset(('direct', 'inferred', 'reported', 'contradicts')),
    ('intents', 'type'): frozenset((
        'need', 'obligation', 'quest', 'agenda', 'aspiration', 'relationship', 'habit', 'reaction',
    )),
    ('intents', 'status'): frozenset(('active', 'paused', 'completed', 'failed', 'abandoned')),
    ('intents', 'horizon'): frozenset(('immediate', 'short', 'day', 'long', 'open_ended')),
    ('entity_relationships', 'scope_type'): frozenset(('world', 'simulation')),
    ('entity_relationships', 'visibility'): frozenset(('public', 'private', 'objective')),
    ('subjective_entity_claims', 'category'): frozenset((
        'appearance', 'personality', 'preference', 'aversion', 'capability', 'habit', 'value',
        'relationship_expectation', 'identity', 'state', 'safety', 'access', 'contents', 'purpose',
        'condition', 'ownership', 'risk', 'history', 'other',
    )),
    ('subjective_entity_claims', 'stance'): frozenset((
        'believes', 'suspects', 'uncertain', 'doubts', 'denies',
    )),
    ('entity_variable_sets', 'owner_type'): frozenset((
        'world', 'character', 'background_character', 'item', 'item_stack', 'equipment',
        'container', 'location', 'landmark', 'body', 'unknown',
    )),
}
WORLD_REFERENCE_FIELDS = {
    'parent_location_id': 'locations', 'location_id': 'locations', 'landmark_id': 'landmarks',
    'item_id': 'items', 'unlocking_item_ids': 'items', 'held_stack_ids': 'item_stacks',
    'held_equipment_ids': 'equipment', 'held_container_ids': 'containers', 'turn_ids': 'turns',
    'event_id': 'events', 'created_by_event_id': 'events', 'contributed_by_event_ids': 'events',
    'character_id': 'characters', 'observer_character_id': 'characters',
    'perspective_character_id': 'characters', 'evidence_memory_ids': 'memories',
    'supporting_memory_ids': 'memories', 'contradicting_memory_ids': 'memories',
}
PHYSICAL_SECTIONS = frozenset((
    'world', 'locations', 'landmarks', 'characters', 'background_characters', 'items',
    'item_stacks', 'equipment', 'containers',
))
PHYSICAL_ENTITY_TYPES = frozenset((
    'world', 'character', 'background_character', 'item', 'item_stack', 'equipment',
    'container', 'location', 'landmark', 'body', 'unknown',
))


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
        world_tags = (self.world.get('metadata') or {}).get('tags', [])
        if not isinstance(world_tags, list) or not all(isinstance(tag, str) for tag in world_tags):
            raise ValueError('World metadata tags must be a list of strings')
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
        ids_by_section = {
            section: {str(row['id']) for row in self.sections.get(section, [])}
            for section in WORLD_SECTION_NAMES
        }
        ids_by_section['world'] = {str(self.world['id'])}
        physical_ids = {
            entity_id for entity_id, section in ids.items() if section in PHYSICAL_SECTIONS
        }

        for section, rows in self.sections.items():
            for index, row in enumerate(rows):
                path = f'{section}[{index}]'
                for field, value in row.items():
                    allowed = WORLD_ENUM_FIELDS.get((section, field))
                    if allowed is not None and value not in allowed:
                        raise ValueError(f'{path}.{field} has invalid value {value!r}')
                    target_section = WORLD_REFERENCE_FIELDS.get(field)
                    accepted_ids = ids_by_section.get(target_section) if target_section else None
                    if field in ('owner_id', 'holder_id'):
                        accepted_ids = physical_ids
                    if accepted_ids is not None:
                        references = value if isinstance(value, list) else (value,)
                        for reference in references:
                            if reference is not None and str(reference) not in accepted_ids:
                                raise ValueError(f'{path}.{field} references unknown id {reference!r}')

                if section in ('item_stacks', 'equipment', 'containers'):
                    if row.get('location_id') and row.get('holder_id'):
                        raise ValueError(f'{path} cannot have both location_id and holder_id')

                for field in ('source', 'target', 'subject'):
                    reference = row.get(field)
                    if not isinstance(reference, dict):
                        continue
                    if reference.get('type') not in PHYSICAL_ENTITY_TYPES:
                        raise ValueError(f'{path}.{field}.type has invalid value {reference.get("type")!r}')
                    if reference.get('id') not in physical_ids:
                        raise ValueError(f'{path}.{field} references unknown id {reference.get("id")!r}')

                if section == 'entity_relationships':
                    source = row.get('source') or {}
                    target = row.get('target') or {}
                    if source.get('id') and source.get('id') == target.get('id'):
                        raise ValueError(f'{path} source and target must be different entities')
                    if (row.get('visibility') == 'private' or row.get('private_description')) \
                            and not row.get('perspective_character_id'):
                        raise ValueError(f'{path} private relationship requires perspective_character_id')
                    details = row.get('details')
                    if isinstance(details, dict):
                        kinds = frozenset(('interpersonal', 'spatial', 'interaction', 'goal', 'compatibility', 'generic'))
                        if details.get('kind') not in kinds:
                            raise ValueError(f'{path}.details.kind has invalid value {details.get("kind")!r}')
                        if details.get('kind') == 'interpersonal' and (
                                source.get('type') != 'character' or target.get('type') != 'character'):
                            raise ValueError(f'{path} interpersonal relationship endpoints must be characters')

                if section == 'subjective_entity_claims':
                    if bool(row.get('simulation_id')) == bool(row.get('world_id')):
                        raise ValueError(f'{path} must belong to exactly one world or simulation')
                    subject = row.get('subject') or {}
                    if subject.get('id') == row.get('observer_character_id'):
                        raise ValueError(f'{path} subject must differ from observer_character_id')
                    supporting = set(row.get('supporting_memory_ids') or [])
                    contradicting = set(row.get('contradicting_memory_ids') or [])
                    if supporting & contradicting:
                        raise ValueError(f'{path} cannot use the same memory as support and contradiction')

                if section == 'entity_variable_sets':
                    owner_id = row.get('owner_id')
                    if owner_id is not None and str(owner_id) not in physical_ids:
                        raise ValueError(f'{path}.owner_id references unknown id {owner_id!r}')
                    for variable_index, variable in enumerate(row.get('variables') or []):
                        value_type = variable.get('value_type')
                        if value_type not in ('string', 'integer', 'float', 'boolean'):
                            raise ValueError(
                                f'{path}.variables[{variable_index}].value_type has invalid value {value_type!r}'
                            )
        media_ids: set[str] = set()
        for media in self.media:
            if media.media_id in media_ids:
                raise ValueError(f'Duplicate media id {media.media_id!r}')
            media_ids.add(media.media_id)
        return self


class WorldDataDocument(ResourceDataDocument):
    data: WorldBundleData
