import json

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import ValidationError

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import (
    CommonModel,
    Resource,
    ResourceType,
    SillyTavernPresetData,
    SillyTavernPresetDataDocument,
)
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.components import get_editable_resource
from .utils import AuthenticatedUserDependency, DatabaseDependency


preset_router = APIRouter(prefix='/resources', tags=['SillyTavern Presets'])


class PresetImportResponse(CommonModel):
    resource: Resource
    draft: SillyTavernPresetDataDocument


@preset_router.post('/{resource_id}/import-preset', response_model=PresetImportResponse)
async def import_preset(resource_id: str,
                        user: AuthenticatedUserDependency,
                        database: DatabaseDependency,
                        file: UploadFile = File(...)) -> PresetImportResponse:
    resource = await get_editable_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_PRESET,
    )
    payload = await file.read(CONFIG.preset_max_bytes + 1)
    if len(payload) > CONFIG.preset_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 'Preset is too large')
    try:
        raw = json.loads(payload.decode('utf-8-sig'))
        if not isinstance(raw, dict):
            raise ValueError('Preset JSON must contain an object')
        data = SillyTavernPresetData.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, 'File is not a valid SillyTavern preset JSON',
        ) from error

    existing = (
        await database.silly_tavern_preset_data.get(resource.draft_data_id)
        if resource.draft_data_id else None
    )
    draft = (
        existing.model_copy(update={'data': data, 'updated_at': utc_now()})
        if existing else SillyTavernPresetDataDocument(resourceId=resource.id, data=data)
    )

    async def persist() -> Resource:
        if existing:
            await database.silly_tavern_preset_data.update(draft)
        else:
            await database.silly_tavern_preset_data.create(draft)
        return await database.resource.update(resource.model_copy(update={
            'draft_data_id': draft.id, 'updated_at': utc_now(),
        }))

    updated = await database.transaction(persist)
    return PresetImportResponse(resource=updated, draft=draft)
