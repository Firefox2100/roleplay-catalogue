from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from roleplay_catalogue.misc import ResourceType, ResourceVisibility
from roleplay_catalogue.models import (
    ImageDataDocument,
    LorebookReference,
    Resource,
    ResourceVersion,
    User,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCardV3LoreBook,
    SillyTavernLorebookDataDocument,
)
from roleplay_catalogue.models.roleplay_resource.silly_tavern.card_v3 import (
    SillyTavernCardV3BookEntry,
    SillyTavernCardV3Data,
)
from roleplay_catalogue.components.resource_publishing import (
    build_character_artifact,
    compute_release_content_diff,
    merge_linked_lorebooks,
    render_merged_character_data,
    resolve_download_asset,
    snapshot_lorebook_references,
)


AUTHOR = User(id='author-id', username='author', email='author@example.com', passwordHash='hash')
LOREBOOK_AUTHOR = User(
    id='lorebook-author-id', username='lorebook-author', email='lb@example.com', passwordHash='hash',
)


def entry(key: str, content: str, order: int = 0) -> SillyTavernCardV3BookEntry:
    return SillyTavernCardV3BookEntry(
        keys=[key], content=content, enabled=True, insertion_order=order,
        use_regex=False, constant=False,
    )


def lorebook_resource(*, resource_id='lorebook-id', author_id=LOREBOOK_AUTHOR.id,
                      visibility=ResourceVisibility.PUBLIC, draft_data_id=None,
                      co_author_ids=()) -> Resource:
    return Resource(
        id=resource_id, resourceType=ResourceType.SILLY_TAVERN_LOREBOOK, authorId=author_id,
        coAuthorIds=co_author_ids, draftDataId=draft_data_id,
        metadata={'name': 'Lore', 'visibility': visibility},
    )


class Repo:
    def __init__(self, documents=()):
        self.documents = {document.id: document for document in documents}

    async def get(self, item_id):
        return self.documents.get(item_id)


class VersionRepo(Repo):
    async def get_latest(self, resource_id):
        matching = [item for item in self.documents.values() if item.resource_id == resource_id]
        return max(matching, key=lambda item: item.version_number) if matching else None


class UserRepo(Repo):
    def __init__(self, users=()):
        super().__init__(users)

    async def get(self, user_id):
        return self.documents.get(user_id)


class FakeDatabase:
    def __init__(self, *, resources=(), versions=(), lorebook_documents=(),
                users=(), image_documents=()):
        self.resource = Repo(resources)
        self.resource_version = VersionRepo(versions)
        self.silly_tavern_lorebook_data = Repo(lorebook_documents)
        self.user = UserRepo(users)
        self.image_data = Repo(image_documents)


def lorebook_version(*, version_id='lorebook-version-id', resource_id='lorebook-id',
                     data_id='lorebook-data-id', visibility=ResourceVisibility.PUBLIC,
                     version_number=1) -> ResourceVersion:
    return ResourceVersion(
        id=version_id, resourceId=resource_id, resourceType=ResourceType.SILLY_TAVERN_LOREBOOK,
        versionNumber=version_number, dataId=data_id,
        metadata={'name': 'Lore', 'visibility': visibility}, visibility=visibility,
        publishedById=LOREBOOK_AUTHOR.id,
    )


def lorebook_document(*, data_id='lorebook-data-id', resource_id='lorebook-id',
                      resource_version_id=None, entries=()) -> SillyTavernLorebookDataDocument:
    return SillyTavernLorebookDataDocument(
        id=data_id, resourceId=resource_id, resourceVersionId=resource_version_id,
        data=SillyTavernCardV3LoreBook(entries=list(entries)),
    )


async def test_merge_links_a_published_lorebook_release_and_credits_its_author() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource()],
        versions=[lorebook_version()],
        lorebook_documents=[lorebook_document(entries=[entry('a', 'Lore content')])],
        users=[LOREBOOK_AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    merged = await merge_linked_lorebooks(
        character, (link,), database,
        character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
    )

    assert merged.character_book.entries[0].content == 'Lore content'
    assert merged.character_book.author == LOREBOOK_AUTHOR.username


async def test_merge_retains_embedded_book_settings_as_base_and_orders_authors() -> None:
    character = SillyTavernCardV3Data(
        name='Character',
        character_book=SillyTavernCardV3LoreBook(
            scan_depth=7, entries=[entry('own', 'Embedded content')],
        ),
    )
    database = FakeDatabase(
        resources=[lorebook_resource()],
        versions=[lorebook_version()],
        lorebook_documents=[lorebook_document(entries=[entry('shared', 'Linked content')])],
        users=[LOREBOOK_AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    merged = await merge_linked_lorebooks(
        character, (link,), database,
        character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
    )

    assert merged.character_book.scan_depth == 7
    assert [item.content for item in merged.character_book.entries] == [
        'Embedded content', 'Linked content',
    ]
    assert merged.character_book.author == f'{AUTHOR.username}, {LOREBOOK_AUTHOR.username}'


async def test_merge_preserves_link_order_across_multiple_lorebooks() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(resource_id='lorebook-1'),
                   lorebook_resource(resource_id='lorebook-2')],
        versions=[
            lorebook_version(version_id='v1', resource_id='lorebook-1', data_id='data-1'),
            lorebook_version(version_id='v2', resource_id='lorebook-2', data_id='data-2'),
        ],
        lorebook_documents=[
            lorebook_document(data_id='data-1', resource_id='lorebook-1',
                              entries=[entry('first', 'First content')]),
            lorebook_document(data_id='data-2', resource_id='lorebook-2',
                              entries=[entry('second', 'Second content')]),
        ],
        users=[LOREBOOK_AUTHOR],
    )
    links = (
        LorebookReference(resourceId='lorebook-1', versionId='v1'),
        LorebookReference(resourceId='lorebook-2', versionId='v2'),
    )

    merged = await merge_linked_lorebooks(
        character, links, database,
        character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
    )

    assert [item.content for item in merged.character_book.entries] == [
        'First content', 'Second content',
    ]


async def test_merge_rejects_link_to_a_resource_that_no_longer_exists() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase()
    link = LorebookReference(resourceId='missing', versionId='some-version')

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
        )
    assert excinfo.value.status_code == 409
    assert 'no longer exists' in excinfo.value.detail


async def test_merge_requires_a_release_when_publishing() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(resources=[lorebook_resource(co_author_ids=(AUTHOR.id,))])
    link = LorebookReference(resourceId='lorebook-id', versionId=None)

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
            require_releases=True,
        )
    assert excinfo.value.status_code == 409
    assert 'cannot link lorebook drafts' in excinfo.value.detail


async def test_merge_rejects_a_version_that_does_not_belong_to_the_linked_resource() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(), lorebook_resource(resource_id='other-lorebook')],
        versions=[lorebook_version(resource_id='other-lorebook')],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
        )
    assert excinfo.value.status_code == 409
    assert 'invalid' in excinfo.value.detail


async def test_merge_rejects_a_private_release_the_character_editors_cannot_read() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(visibility=ResourceVisibility.PRIVATE)],
        versions=[lorebook_version(visibility=ResourceVisibility.PRIVATE)],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
        )
    assert excinfo.value.status_code == 409
    assert 'no longer readable' in excinfo.value.detail


async def test_merge_allows_a_private_release_the_character_editors_can_read() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(visibility=ResourceVisibility.PRIVATE, author_id=AUTHOR.id)],
        versions=[lorebook_version(visibility=ResourceVisibility.PRIVATE)],
        lorebook_documents=[lorebook_document(entries=[entry('a', 'Private content')])],
        users=[AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    merged = await merge_linked_lorebooks(
        character, (link,), database,
        character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
    )
    assert merged.character_book.entries[0].content == 'Private content'


@pytest.mark.parametrize(('required_visibility', 'link_visibility'), [
    (ResourceVisibility.PUBLIC, ResourceVisibility.AUTHENTICATED),
    (ResourceVisibility.AUTHENTICATED, ResourceVisibility.PRIVATE),
])
async def test_merge_rejects_a_release_less_visible_than_required(
        required_visibility, link_visibility) -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(visibility=link_visibility, author_id=AUTHOR.id)],
        versions=[lorebook_version(visibility=link_visibility)],
        lorebook_documents=[lorebook_document()],
        users=[AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
            required_visibility=required_visibility,
        )
    assert excinfo.value.status_code == 409
    assert 'less visible' in excinfo.value.detail


async def test_merge_allows_a_draft_link_when_editors_overlap() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource(author_id=AUTHOR.id, draft_data_id='draft-data-id')],
        lorebook_documents=[lorebook_document(
            data_id='draft-data-id', entries=[entry('a', 'Draft content')],
        )],
        users=[AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId=None)

    merged = await merge_linked_lorebooks(
        character, (link,), database,
        character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
    )
    assert merged.character_book.entries[0].content == 'Draft content'


async def test_merge_rejects_a_draft_link_the_character_editors_cannot_edit() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(resources=[lorebook_resource(author_id=LOREBOOK_AUTHOR.id)])
    link = LorebookReference(resourceId='lorebook-id', versionId=None)

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
        )
    assert excinfo.value.status_code == 409
    assert 'Only editable lorebook drafts' in excinfo.value.detail


async def test_merge_rejects_a_link_with_no_resolvable_content() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        resources=[lorebook_resource()],
        versions=[lorebook_version()],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    with pytest.raises(HTTPException) as excinfo:
        await merge_linked_lorebooks(
            character, (link,), database,
            character_author_name=AUTHOR.username, character_editor_ids=frozenset({AUTHOR.id}),
        )
    assert excinfo.value.status_code == 409
    assert 'no selected content' in excinfo.value.detail


async def test_render_merged_character_data_never_raises_and_skips_unresolved_links() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase()
    unresolved = LorebookReference(
        resourceId='gone', versionId='missing-version', author='Someone',
    )
    draft_only = LorebookReference(resourceId='draft-only', versionId=None)

    merged = await render_merged_character_data(
        character, (unresolved, draft_only), database, character_author_name=AUTHOR.username,
    )

    assert merged == character


async def test_render_merged_character_data_embeds_resolvable_pinned_releases() -> None:
    character = SillyTavernCardV3Data(name='Character')
    database = FakeDatabase(
        versions=[lorebook_version()],
        lorebook_documents=[lorebook_document(entries=[entry('a', 'Pinned content')])],
    )
    link = LorebookReference(
        resourceId='lorebook-id', versionId='lorebook-version-id', author='Pinned Author',
    )

    merged = await render_merged_character_data(
        character, (link,), database, character_author_name=AUTHOR.username,
    )

    assert merged.character_book.entries[0].content == 'Pinned content'
    assert merged.character_book.author == 'Pinned Author'


class DataRepo:
    def __init__(self, documents):
        self.documents = documents

    async def get(self, data_id):
        return self.documents.get(data_id)


async def test_compute_release_content_diff_merges_lorebooks_for_characters() -> None:
    database = FakeDatabase(
        versions=[lorebook_version()],
        lorebook_documents=[lorebook_document(entries=[entry('a', 'Linked content')])],
    )
    current_data = SillyTavernCardV3Data(name='Character')
    links = (LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id',
                               author='Lore Author'),)

    diff = await compute_release_content_diff(
        resource=Resource(
            resourceType=ResourceType.SILLY_TAVERN_CHARACTER, authorId=AUTHOR.id,
            metadata={'name': 'Character'},
        ),
        repository=DataRepo({}),
        database=database,
        latest=None,
        current_data=current_data,
        release_lorebooks=links,
        author_username=AUTHOR.username,
    )

    assert diff is not None
    assert 'Linked content' in diff
    assert not [line for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]


async def test_compute_release_content_diff_uses_raw_payload_for_non_character_types() -> None:
    database = FakeDatabase()
    current = SillyTavernCardV3LoreBook(entries=[entry('a', 'Updated')])
    latest = lorebook_version(data_id='previous-data')

    diff = await compute_release_content_diff(
        resource=Resource(
            resourceType=ResourceType.SILLY_TAVERN_LOREBOOK, authorId=AUTHOR.id,
            metadata={'name': 'Lore'},
        ),
        repository=DataRepo({'previous-data': lorebook_document(entries=[entry('a', 'Original')])}),
        database=database,
        latest=latest,
        current_data=current,
        release_lorebooks=(),
        author_username=AUTHOR.username,
    )

    removed = [line for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]
    added = [line for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
    assert any('"content": "Original"' in line for line in removed)
    assert any('"content": "Updated"' in line for line in added)


async def test_snapshot_lorebook_references_rejects_draft_links() -> None:
    database = FakeDatabase()
    link = LorebookReference(resourceId='lorebook-id', versionId=None)

    with pytest.raises(HTTPException) as excinfo:
        await snapshot_lorebook_references((link,), database)
    assert excinfo.value.status_code == 409
    assert 'cannot link lorebook drafts' in excinfo.value.detail


async def test_snapshot_lorebook_references_fills_in_name_author_and_version() -> None:
    database = FakeDatabase(
        resources=[lorebook_resource(author_id=LOREBOOK_AUTHOR.id)],
        versions=[lorebook_version()],
        users=[LOREBOOK_AUTHOR],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    snapshots = await snapshot_lorebook_references((link,), database)

    assert snapshots[0].name == 'Lore'
    assert snapshots[0].author == LOREBOOK_AUTHOR.username
    assert snapshots[0].version == '1'


async def test_snapshot_lorebook_references_rejects_a_version_from_another_resource() -> None:
    database = FakeDatabase(
        resources=[lorebook_resource()],
        versions=[lorebook_version(resource_id='other-lorebook')],
    )
    link = LorebookReference(resourceId='lorebook-id', versionId='lorebook-version-id')

    with pytest.raises(HTTPException) as excinfo:
        await snapshot_lorebook_references((link,), database)
    assert excinfo.value.status_code == 409
    assert 'invalid' in excinfo.value.detail


async def test_resolve_download_asset_prefers_the_stored_artifact() -> None:
    version = ResourceVersion(
        resourceId='r', resourceType=ResourceType.SILLY_TAVERN_CHARACTER, versionNumber=1,
        dataId='data', metadata={'name': 'Character'}, publishedById=AUTHOR.id,
        artifactObjectKey='releases/character.json', artifactContentType='application/json',
        artifactFileName='Character.json', artifactByteSize=42, artifactSha256='deadbeef',
    )

    key, content_type, file_name, byte_size, sha256 = await resolve_download_asset(
        version, FakeDatabase(),
    )

    assert (key, content_type, file_name, byte_size, sha256) == (
        'releases/character.json', 'application/json', 'Character.json', 42, 'deadbeef',
    )


async def test_resolve_download_asset_falls_back_to_image_data_for_images() -> None:
    version = ResourceVersion(
        resourceId='image-id', resourceType=ResourceType.IMAGE, versionNumber=1,
        dataId='image-data', metadata={'name': 'Cover'}, publishedById=AUTHOR.id,
    )
    document = ImageDataDocument(
        resourceId='image-id', objectKey='images/cover.png', contentType='image/png',
        byteSize=10, sha256='a' * 64, width=1, height=1,
    )
    database = FakeDatabase()
    database.image_data = DataRepo({'image-data': document})

    key, content_type, file_name, byte_size, sha256 = await resolve_download_asset(version, database)

    assert key == 'images/cover.png'
    assert content_type == 'image/png'
    assert file_name == 'Cover.png'
    assert (byte_size, sha256) == (10, 'a' * 64)


async def test_resolve_download_asset_404s_when_nothing_resolves() -> None:
    version = ResourceVersion(
        resourceId='r', resourceType=ResourceType.SILLY_TAVERN_LOREBOOK, versionNumber=1,
        dataId='data', metadata={'name': 'Lore'}, publishedById=AUTHOR.id,
    )

    with pytest.raises(HTTPException) as excinfo:
        await resolve_download_asset(version, FakeDatabase())
    assert excinfo.value.status_code == 404


def _make_cover_png() -> bytes:
    buffer = BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(buffer, format='PNG')
    return buffer.getvalue()


class FakeStorage:
    def __init__(self, objects):
        self.objects = objects

    async def fetch(self, key):
        yield self.objects[key]


async def test_build_character_artifact_returns_json_without_a_cover() -> None:
    card = SillyTavernCardV3Data(name='Character')

    payload, content_type, extension = await build_character_artifact(
        database=FakeDatabase(), storage=FakeStorage({}), card=card, cover_image_resource_id=None,
    )

    assert content_type == 'application/json'
    assert extension == '.json'
    assert b'"name":"Character"' in payload


async def test_build_character_artifact_packages_a_png_with_a_cover() -> None:
    card = SillyTavernCardV3Data(name='Character')
    image_version = ResourceVersion(
        resourceId='cover-id', resourceType=ResourceType.IMAGE, versionNumber=1,
        dataId='cover-data', metadata={'name': 'Cover'}, publishedById=AUTHOR.id,
    )
    document = ImageDataDocument(
        resourceId='cover-id', objectKey='images/cover.png', contentType='image/png',
        byteSize=1, sha256='a' * 64, width=4, height=4,
    )
    database = FakeDatabase(versions=[image_version])
    database.image_data = DataRepo({'cover-data': document})
    storage = FakeStorage({'images/cover.png': _make_cover_png()})

    payload, content_type, extension = await build_character_artifact(
        database=database, storage=storage, card=card, cover_image_resource_id='cover-id',
    )

    assert content_type == 'image/png'
    assert extension == '.png'
    assert payload.startswith(b'\x89PNG\r\n\x1a\n')


async def test_build_character_artifact_rejects_a_cover_with_missing_content() -> None:
    card = SillyTavernCardV3Data(name='Character')
    image_version = ResourceVersion(
        resourceId='cover-id', resourceType=ResourceType.IMAGE, versionNumber=1,
        dataId='cover-data', metadata={'name': 'Cover'}, publishedById=AUTHOR.id,
    )
    database = FakeDatabase(versions=[image_version])

    with pytest.raises(HTTPException) as excinfo:
        await build_character_artifact(
            database=database, storage=FakeStorage({}), card=card,
            cover_image_resource_id='cover-id',
        )
    assert excinfo.value.status_code == 409
    assert 'Cover image content is missing' in excinfo.value.detail
