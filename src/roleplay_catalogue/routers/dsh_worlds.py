"""Upload endpoints for native DeepSeek Harness agentic-roleplay worlds."""

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from roleplay_catalogue.components import (
    DshWorldBundleError, create_image_resource, get_editable_resource,
    parse_dsh_world_bundle,
)
from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import CommonModel, DshWorldDataDocument, Resource, ResourceType
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from .utils import AuthenticatedUserDependency, DatabaseDependency, StorageDependency


dsh_world_router = APIRouter(prefix='/resources', tags=['DeepSeek Harness Worlds'])


class DshWorldImportResponse(CommonModel):
    """Updated resource and its indexed draft package."""
    resource: Resource
    draft: DshWorldDataDocument


@dsh_world_router.post('/{resource_id}/import-dsh-world', response_model=DshWorldImportResponse)
# Cover ingestion and atomic package replacement keep this endpoint intentionally cohesive.
# pylint: disable-next=too-many-locals
async def import_dsh_world(resource_id: str,
                           user: AuthenticatedUserDependency,
                           database: DatabaseDependency,
                           storage: StorageDependency,
                           file: UploadFile = File(...)) -> DshWorldImportResponse:
    """Validate and store a replacement native world-folder ZIP."""
    resource = await get_editable_resource(
        database, resource_id, user, ResourceType.DSH_AGENTIC_ROLEPLAY_WORLD,
    )
    payload = await file.read(CONFIG.dsh_world_max_bytes + 1)
    if len(payload) > CONFIG.dsh_world_max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, 'World ZIP is too large')
    object_key = f'drafts/dsh-worlds/{resource.id}/{uuid4()}.zip'
    try:
        parsed = parse_dsh_world_bundle(payload, object_key)
    except DshWorldBundleError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error

    payload = parsed.payload
    data = parsed.data
    cover = None
    if parsed.cover:
        cover = await create_image_resource(
            name=f'Cover image for {data.world_name}',
            description='', visibility=resource.metadata.visibility,
            tags=list(resource.metadata.tags), language=resource.metadata.language,
            source=parsed.cover, user=user, database=database, storage=storage,
        )
    existing = (
        await database.dsh_world_data.get(resource.draft_data_id)
        if resource.draft_data_id else None
    )
    draft = (
        existing.model_copy(update={'data': data, 'updated_at': utc_now()})
        if existing else DshWorldDataDocument(resourceId=resource.id, data=data)
    )
    await storage.upload(object_key, payload, 'application/zip')
    try:
        await storage.wait_until_available(object_key)

        async def persist() -> Resource:
            if existing:
                await database.dsh_world_data.update(draft)
            else:
                await database.dsh_world_data.create(draft)
            updated_resource = await database.resource.apply_update(
                resource.id, {
                    'draftDataId': draft.id,
                    'coverImageResourceId': cover.id if cover else None,
                },
            )
            if not updated_resource:
                raise RuntimeError('Resource disappeared while importing its world ZIP')
            return updated_resource

        updated = await database.transaction(persist)
    except Exception:
        await storage.remove(object_key)
        raise
    if existing:
        await storage.remove(existing.data.object_key)
    return DshWorldImportResponse(resource=updated, draft=draft)
