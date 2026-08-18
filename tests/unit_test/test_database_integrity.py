from roleplay_catalogue.services.database.integrity import check_integrity


class EmptyCursor:
    async def to_list(self, length):
        assert length == 1
        return []


class Collection:
    def __init__(self):
        self.aggregate_calls = 0

    async def aggregate(self, pipeline):
        assert pipeline
        self.aggregate_calls += 1
        return EmptyCursor()


class Database:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, Collection())


async def test_integrity_check_awaits_async_aggregate_cursor() -> None:
    database = Database()

    assert await check_integrity(database) == []
    assert sum(collection.aggregate_calls for collection in database.collections.values()) == 17
