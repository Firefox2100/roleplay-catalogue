from pymongo.asynchronous.database import AsyncDatabase


REVISIONED_COLLECTIONS = (
    'resources',
    'sillytavern_character_data',
    'sillytavern_lorebook_data',
    'sillytavern_preset_data',
    'image_data',
    'world_data',
)


async def backfill_revisions(database: AsyncDatabase,
                             collections: tuple[str, ...] = REVISIONED_COLLECTIONS,
                             ) -> None:
    """Idempotently seed the `revision` optimistic-concurrency counter on documents
    written before it existed; a missing field can't match an equality filter, so
    `update_if_match` would otherwise reject every write against a pre-existing document.
    """
    for collection_name in collections:
        await database[collection_name].update_many(
            {'revision': {'$exists': False}},
            {'$set': {'revision': 0}},
        )
