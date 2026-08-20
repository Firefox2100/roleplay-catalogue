from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from roleplay_catalogue.misc import UserStatus
from roleplay_catalogue.models import Resource, ResourceType, ResourceVersion, User
from roleplay_catalogue.components import AccountComponent


class Repository:
    def __init__(self, documents=()):
        self.documents = {document.id: document for document in documents}

    async def get(self, item_id):
        return self.documents.get(item_id)

    async def delete(self, item_id):
        return self.documents.pop(item_id, None) is not None


class ResourceRepository(Repository):
    async def list_by_author(self, author_id):
        return [item for item in self.documents.values() if item.author_id == author_id]

    async def clear_cover_reference(self, image_id):
        for item_id, item in list(self.documents.items()):
            if item.cover_image_resource_id == image_id:
                self.documents[item_id] = item.model_copy(update={'cover_image_resource_id': None})

    async def remove_co_author(self, user_id):
        for item_id, item in list(self.documents.items()):
            if user_id in item.co_author_ids:
                self.documents[item_id] = item.model_copy(update={
                    'co_author_ids': tuple(
                        existing_id for existing_id in item.co_author_ids if existing_id != user_id
                    ),
                })


class VersionRepository(Repository):
    async def list_all_for_resource(self, resource_id):
        return [item for item in self.documents.values() if item.resource_id == resource_id]


class UserRepository(Repository):
    async def list_pending_before(self, cutoff):
        return [item for item in self.documents.values()
                if item.status == UserStatus.PENDING_ACTIVATION and item.created_at <= cutoff]


class TokenRepository:
    def __init__(self):
        self.deleted = []

    async def delete(self, key):
        self.deleted.append(key)
        return True

    async def delete_for_user(self, user_id):
        self.deleted.append(user_id)
        return 1


class MetricsRepository:
    def __init__(self):
        self.deleted = []

    async def delete(self, resource_id):
        self.deleted.append(resource_id)
        return True


class Storage:
    def __init__(self, keys):
        self.keys = set(keys)

    async def remove(self, key):
        self.keys.discard(key)


async def test_account_deletion_cascades_resources_versions_data_and_storage() -> None:
    user = User(id='user', username='alice', email='alice@example.com', passwordHash='hash')
    character = Resource(
        id='character', resourceType=ResourceType.SILLY_TAVERN_CHARACTER,
        authorId=user.id, metadata={'name': 'Character'}, draftDataId='draft',
    )
    image = Resource(
        id='image', resourceType=ResourceType.IMAGE, authorId=user.id,
        metadata={'name': 'Image'},
    )
    character_version = ResourceVersion(
        id='character-version', resourceId=character.id, resourceType=character.resource_type,
        versionNumber=1, dataId='snapshot', metadata=character.metadata,
        publishedById=user.id, artifactObjectKey='releases/character.json',
    )
    image_version = ResourceVersion(
        id='image-version', resourceId=image.id, resourceType=image.resource_type,
        versionNumber=1, dataId='image-data', metadata=image.metadata, publishedById=user.id,
    )
    character_data = Repository((SimpleNamespace(id='draft'), SimpleNamespace(id='snapshot')))
    image_data = Repository((SimpleNamespace(id='image-data', object_key='images/image.png'),))
    database = SimpleNamespace(
        user=UserRepository((user,)), resource=ResourceRepository((character, image)),
        resource_version=VersionRepository((character_version, image_version)),
        silly_tavern_character_data=character_data,
        silly_tavern_lorebook_data=Repository(), image_data=image_data,
        activation_token=TokenRepository(), password_reset_token=TokenRepository(),
        api_key=TokenRepository(), resource_metrics=MetricsRepository(),
        transaction=lambda operation: operation(),
    )
    storage = Storage({'releases/character.json', 'images/image.png'})

    await AccountComponent(database, database, storage, 86400).delete_account(user)

    assert not database.user.documents
    assert not database.resource.documents
    assert not database.resource_version.documents
    assert not character_data.documents
    assert not image_data.documents
    assert not storage.keys


async def test_pending_account_cleanup_uses_account_creation_time() -> None:
    expired = User(
        id='expired', username='expired', email='expired@example.com', passwordHash='hash',
        status=UserStatus.PENDING_ACTIVATION,
        createdAt=datetime.now(timezone.utc) - timedelta(hours=25),
    )
    database = SimpleNamespace(
        user=UserRepository((expired,)), resource=ResourceRepository(),
        resource_version=VersionRepository(), silly_tavern_character_data=Repository(),
        silly_tavern_lorebook_data=Repository(), image_data=Repository(),
        activation_token=TokenRepository(), password_reset_token=TokenRepository(),
        api_key=TokenRepository(), resource_metrics=MetricsRepository(),
        transaction=lambda operation: operation(),
    )

    purged = await AccountComponent(
        database, database, Storage(set()), 86400,
    ).purge_expired_pending_accounts()

    assert purged == 1
    assert not database.user.documents
