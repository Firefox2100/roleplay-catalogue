from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.asynchronous.database import AsyncDatabase


@dataclass(frozen=True)
class IndexDefinition:
    collection: str
    name: str
    keys: Any
    options: dict[str, Any]


INDEXES: tuple[IndexDefinition, ...] = (
    IndexDefinition('users', 'users_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('users', 'users_username_unique', [('username', ASCENDING)], {'unique': True}),
    IndexDefinition('users', 'users_email_unique', [('email', ASCENDING)], {'unique': True}),
    IndexDefinition('users', 'users_pending_cleanup', [('status', ASCENDING), ('createdAt', ASCENDING)], {}),
    IndexDefinition('activation_tokens', 'activation_username_unique', [('username', ASCENDING)], {'unique': True}),
    IndexDefinition('activation_tokens', 'activation_expiry_ttl', [('expiresAt', ASCENDING)], {'expireAfterSeconds': 0}),
    IndexDefinition('password_reset_tokens', 'password_reset_user_unique', [('userId', ASCENDING)], {'unique': True}),
    IndexDefinition('password_reset_tokens', 'password_reset_expiry_ttl', [('expiresAt', ASCENDING)], {'expireAfterSeconds': 0}),
    IndexDefinition('api_keys', 'api_keys_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('api_keys', 'api_keys_user_created', [('userId', ASCENDING), ('createdAt', DESCENDING)], {}),
    IndexDefinition('api_keys', 'api_keys_expiry_ttl', [('expiresAt', ASCENDING)], {'expireAfterSeconds': 0}),
    IndexDefinition('resources', 'resources_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('resources', 'resources_author_updated', [('authorId', ASCENDING), ('updatedAt', DESCENDING)], {}),
    IndexDefinition('resources', 'resources_visibility_updated', [('metadata.visibility', ASCENDING), ('updatedAt', DESCENDING)], {}),
    IndexDefinition('resources', 'resources_type_updated', [('resourceType', ASCENDING), ('updatedAt', DESCENDING)], {}),
    IndexDefinition('resources', 'resources_language_updated', [('metadata.language', ASCENDING), ('updatedAt', DESCENDING)], {}),
    IndexDefinition('resources', 'resources_tags', [('metadata.tags', ASCENDING)], {}),
    IndexDefinition('resources', 'resources_linked_lorebooks', [('linkedLorebookResourceIds', ASCENDING)], {}),
    IndexDefinition(
        'resources', 'resources_catalogue_text',
        [('metadata.name', TEXT), ('metadata.description', TEXT)],
        {'weights': {'metadata.name': 10, 'metadata.description': 2}, 'default_language': 'none'},
    ),
    IndexDefinition('resource_versions', 'versions_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition(
        'resource_versions', 'versions_resource_number_unique',
        [('resourceId', ASCENDING), ('versionNumber', DESCENDING)], {'unique': True},
    ),
    IndexDefinition('resource_versions', 'versions_cover', [('coverImageResourceId', ASCENDING)], {}),
    IndexDefinition('sillytavern_character_data', 'character_data_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('sillytavern_character_data', 'character_data_resource', [('resourceId', ASCENDING)], {}),
    IndexDefinition('sillytavern_character_data', 'character_data_version', [('resourceVersionId', ASCENDING)], {}),
    IndexDefinition('sillytavern_lorebook_data', 'lorebook_data_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('sillytavern_lorebook_data', 'lorebook_data_resource', [('resourceId', ASCENDING)], {}),
    IndexDefinition('sillytavern_lorebook_data', 'lorebook_data_version', [('resourceVersionId', ASCENDING)], {}),
    IndexDefinition('image_data', 'image_data_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('image_data', 'image_data_resource', [('resourceId', ASCENDING)], {}),
    IndexDefinition('image_data', 'image_data_version', [('resourceVersionId', ASCENDING)], {}),
    IndexDefinition('image_data', 'image_data_sha256', [('sha256', ASCENDING)], {}),
    IndexDefinition('world_data', 'world_data_id_unique', [('id', ASCENDING)], {'unique': True}),
    IndexDefinition('world_data', 'world_data_resource', [('resourceId', ASCENDING)], {}),
    IndexDefinition('world_data', 'world_data_version', [('resourceVersionId', ASCENDING)], {}),
    IndexDefinition('world_data', 'world_data_media_image', [('data.media.imageResourceId', ASCENDING)], {}),
)


async def ensure_indexes(database: AsyncDatabase,
                         definitions: Iterable[IndexDefinition] = INDEXES) -> None:
    by_collection: dict[str, list[IndexDefinition]] = {}
    for definition in definitions:
        by_collection.setdefault(definition.collection, []).append(definition)

    for collection_name, collection_indexes in by_collection.items():
        collection = database[collection_name]
        existing = await collection.index_information()
        for definition in collection_indexes:
            if definition.name in existing:
                continue
            # Older releases created some of these without explicit names.
            # MongoDB rejects a second index with the same keys but a new name,
            # so treat an equivalent legacy index as satisfying the definition.
            if any(
                list(details.get('key', ())) == list(definition.keys)
                and all(details.get(option) == value
                        for option, value in definition.options.items())
                for details in existing.values()
            ):
                continue
            await collection.create_index(
                definition.keys,
                name=definition.name,
                **definition.options,
            )
