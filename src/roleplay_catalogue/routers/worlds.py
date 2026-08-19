from fastapi import APIRouter, File, HTTPException, UploadFile, status

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import (
    CommonModel,
    Resource,
    ResourceMetadata,
    ResourceType,
    WorldDataDocument,
)
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.components import (
    WorldBundleError,
    create_image_resource,
    get_editable_resource,
    parse_world_bundle,
    resource_language_from_world,
)
from .utils import AuthenticatedUserDependency, DatabaseDependency, StorageDependency


world_router = APIRouter(prefix='/resources', tags=['World Simulation Engine Worlds'])


class WorldImportResponse(CommonModel):
    resource: Resource
    draft: WorldDataDocument


@world_router.post('/{resource_id}/import-world', response_model=WorldImportResponse)
async def import_world_bundle(resource_id: str,
                              user: AuthenticatedUserDependency,
                              database: DatabaseDependency,
                              storage: StorageDependency,
                              file: UploadFile = File(...)) -> WorldImportResponse:
    resource = await get_editable_resource(
        database, resource_id, user, ResourceType.WORLD_SIMULATION_WORLD,
    )
    payload = await file.read(CONFIG.world_bundle_max_bytes + 1)
    if len(payload) > CONFIG.world_bundle_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 'World bundle is too large')
    try:
        parsed = parse_world_bundle(payload)
    except WorldBundleError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    references = []
    for reference in parsed.data.media:
        image_bytes = parsed.image_files.get(reference.media_id)
        if image_bytes is None:
            references.append(reference)
            continue
        image = await create_image_resource(
            name=reference.record.get('title') or reference.record.get('filename') or 'World image',
            description=f'Imported media for {resource.metadata.name}',
            visibility=resource.metadata.visibility,
            tags=list(resource.metadata.tags),
            source=image_bytes,
            user=user,
            database=database,
            storage=storage,
        )
        references.append(reference.model_copy(update={'image_resource_id': image.id}))

    data = parsed.data.model_copy(update={'media': references})
    existing = await database.world_data.get(resource.draft_data_id) if resource.draft_data_id else None
    draft = (
        existing.model_copy(update={'data': data, 'updated_at': utc_now()})
        if existing else WorldDataDocument(resourceId=resource.id, data=data)
    )
    cover_media_id = data.world.get('cover_media_id')
    cover = next((item.image_resource_id for item in references
                  if item.media_id == cover_media_id), None)
    imported_language = resource_language_from_world(data.world['language'])
    imported_tags = (data.world.get('metadata') or {}).get('tags', [])
    merged_tags = list(resource.metadata.tags)
    merged_tags.extend(tag for tag in imported_tags if tag not in merged_tags)

    async def persist() -> None:
        if existing:
            await database.world_data.update(draft)
        else:
            await database.world_data.create(draft)
        await database.resource.update(resource.model_copy(update={
            'draft_data_id': draft.id,
            'cover_image_resource_id': cover or resource.cover_image_resource_id,
            'metadata': ResourceMetadata(
                name=resource.metadata.name,
                description=resource.metadata.description or data.world.get('description') or '',
                language=imported_language,
                visibility=resource.metadata.visibility,
                tags=tuple(merged_tags),
            ),
            'updated_at': utc_now(),
        }))

    await database.transaction(persist)
    updated_resource = await database.resource.get(resource.id)
    return WorldImportResponse(resource=updated_resource, draft=draft)
