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
        ('sillytavern_preset_data', 'resourceId', 'resources', 'id',
         'preset documents with a missing resource'),
        ('image_data', 'resourceId', 'resources', 'id', 'image documents with a missing resource'),
        ('world_data', 'resourceId', 'resources', 'id', 'world documents with a missing resource'),
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
        ('sillytavern_preset_data', 'preset snapshots'),
        ('image_data', 'image snapshots'),
        ('world_data', 'world snapshots'),
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

    cursor = await database['world_data'].aggregate([
        {'$unwind': '$data.media'},
        {'$match': {'data.media.imageResourceId': {'$ne': None}}},
        {'$lookup': {
            'from': 'resources',
            'localField': 'data.media.imageResourceId',
            'foreignField': 'id',
            'as': '_integrityImage',
        }},
        {'$match': {'_integrityImage': {'$eq': []}}},
        {'$count': 'count'},
    ])
    result = await cursor.to_list(length=1)
    if result:
        problems.append(f"{result[0]['count']} world media links with a missing image")

    cursor = await database['resources'].aggregate([
        {'$unwind': '$linkedLorebooks'},
        {'$lookup': {
            'from': 'resources',
            'localField': 'linkedLorebooks.resourceId',
            'foreignField': 'id',
            'as': '_integrityLorebook',
        }},
        {'$match': {'_integrityLorebook': {'$eq': []}}},
        {'$count': 'count'},
    ])
    result = await cursor.to_list(length=1)
    if result:
        problems.append(f"{result[0]['count']} character lorebook links with a missing lorebook")
    for collection, label in (
        ('resources', 'character draft lorebook release links'),
        ('resource_versions', 'character release lorebook links'),
    ):
        cursor = await database[collection].aggregate([
            {'$unwind': '$linkedLorebooks'},
            {'$match': {'linkedLorebooks.versionId': {'$ne': None}}},
            {'$lookup': {
                'from': 'resource_versions',
                'localField': 'linkedLorebooks.versionId',
                'foreignField': 'id',
                'as': '_integrityLorebookVersion',
            }},
            {'$match': {'_integrityLorebookVersion': {'$eq': []}}},
            {'$count': 'count'},
        ])
        result = await cursor.to_list(length=1)
        if result:
            problems.append(f"{result[0]['count']} {label} with a missing version")
    return problems
