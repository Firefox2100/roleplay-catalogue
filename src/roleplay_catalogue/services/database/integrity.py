from pymongo.asynchronous.database import AsyncDatabase


async def check_integrity(database: AsyncDatabase) -> list[str]:
    """Return descriptions of dangling database relationships without mutating data."""
    checks = (
        ('resources', 'authorId', 'users', 'id', 'resources with a missing author'),
        ('resource_versions', 'resourceId', 'resources', 'id', 'versions with a missing resource'),
        ('resource_versions', 'publishedById', 'users', 'id', 'versions with a missing publisher'),
        ('sillytavern_character_data', 'resourceId', 'resources', 'id',
         'character documents with a missing resource'),
        ('sillytavern_lorebook_data', 'resourceId', 'resources', 'id',
         'lorebook documents with a missing resource'),
        ('image_data', 'resourceId', 'resources', 'id', 'image documents with a missing resource'),
    )
    problems: list[str] = []
    for source, local_field, target, foreign_field, description in checks:
        cursor = await database[source].aggregate([
            {'$lookup': {
                'from': target,
                'localField': local_field,
                'foreignField': foreign_field,
                'as': '_integrityTarget',
            }},
            {'$match': {'_integrityTarget': {'$eq': []}}},
            {'$count': 'count'},
        ])
        result = await cursor.to_list(length=1)
        if result:
            problems.append(f"{result[0]['count']} {description}")

    for collection, label in (
        ('sillytavern_character_data', 'character snapshots'),
        ('sillytavern_lorebook_data', 'lorebook snapshots'),
        ('image_data', 'image snapshots'),
    ):
        cursor = await database[collection].aggregate([
            {'$match': {'resourceVersionId': {'$ne': None}}},
            {'$lookup': {
                'from': 'resource_versions',
                'localField': 'resourceVersionId',
                'foreignField': 'id',
                'as': '_integrityVersion',
            }},
            {'$match': {'_integrityVersion': {'$eq': []}}},
            {'$count': 'count'},
        ])
        result = await cursor.to_list(length=1)
        if result:
            problems.append(f"{result[0]['count']} {label} with a missing version")
    return problems
