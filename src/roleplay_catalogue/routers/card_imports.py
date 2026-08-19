from base64 import b64decode
from binascii import Error as Base64Error
from json import JSONDecodeError, loads
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image
from pydantic import ValidationError

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.models import CommonModel, Resource, ResourceMetadata, ResourceType
from roleplay_catalogue.models.roleplay_resource.resource import utc_now
from roleplay_catalogue.models.roleplay_resource.silly_tavern import (
    SillyTavernCardV2,
    SillyTavernCardV3,
    SillyTavernCardV3LoreBook,
    SillyTavernCharacterData,
    SillyTavernCharacterDataDocument,
    SillyTavernLorebookDataDocument,
    SillyTavernLorebookV3,
)
from roleplay_catalogue.components import create_image_resource, get_editable_resource
from .utils import AuthenticatedUserDependency, DatabaseDependency, StorageDependency


card_import_router = APIRouter(prefix='/resources', tags=['Card Import'])


class CardImportResponse(CommonModel):
    resource: Resource
    draft: SillyTavernCharacterDataDocument


class LorebookImportResponse(CommonModel):
    resource: Resource
    draft: SillyTavernLorebookDataDocument


def parse_card_json(payload: bytes) -> SillyTavernCharacterData:
    try:
        decoded = loads(payload.decode('utf-8-sig'))
    except (UnicodeDecodeError, JSONDecodeError) as error:
        raise ValueError('Card JSON is not valid UTF-8 JSON') from error

    try:
        v3 = SillyTavernCardV3.model_validate(decoded)
        return SillyTavernCharacterData.model_validate(v3.data.model_dump())
    except ValidationError:
        try:
            v2 = SillyTavernCardV2.model_validate(decoded)
            return SillyTavernCharacterData.model_validate(v2.to_v3().data.model_dump())
        except (ValidationError, ValueError) as error:
            raise ValueError('JSON is not a valid SillyTavern V2 or V3 card') from error


def extract_card_from_png(payload: bytes) -> SillyTavernCharacterData:
    try:
        with Image.open(BytesIO(payload)) as image:
            text_fields = dict(image.text)
    except (Image.DecompressionBombError, OSError) as error:
        raise ValueError('Uploaded PNG is not valid') from error

    for field in ('ccv3', 'chara'):
        encoded = text_fields.get(field)
        if not encoded:
            continue
        try:
            card_json = b64decode(encoded, validate=True)
            return parse_card_json(card_json)
        except (Base64Error, ValueError):
            continue
    raise ValueError('PNG does not contain a valid V2 or V3 character card')


def parse_lorebook_json(payload: bytes) -> SillyTavernCardV3LoreBook:
    try:
        decoded = loads(payload.decode('utf-8-sig'))
    except (UnicodeDecodeError, JSONDecodeError) as error:
        raise ValueError('Lorebook JSON is not valid UTF-8 JSON') from error

    identifier = decoded.get('spec') if isinstance(decoded, dict) else None
    try:
        if identifier == 'lorebook_v3':
            return SillyTavernLorebookV3.model_validate(decoded).data
        if identifier in ('chara_card_v2', 'chara_card_v3'):
            card = parse_card_json(payload)
            if card.character_book is None:
                raise ValueError('Character card does not contain an embedded lorebook')
            return SillyTavernCardV3LoreBook.model_validate(card.character_book.model_dump())
    except ValidationError as error:
        raise ValueError('JSON does not contain a valid V3 lorebook') from error
    raise ValueError('JSON must identify a V3 lorebook or V2/V3 character card')


def extract_lorebook_from_png(payload: bytes) -> SillyTavernCardV3LoreBook:
    card = extract_card_from_png(payload)
    if card.character_book is None:
        raise ValueError('Character card does not contain an embedded lorebook')
    return SillyTavernCardV3LoreBook.model_validate(card.character_book.model_dump())


def merge_missing(current: Any, incoming: Any) -> Any:
    if incoming is None:
        return current
    if current is None or current == '':
        return incoming
    if isinstance(current, list) and isinstance(incoming, list):
        return current + [item for item in incoming if item not in current]
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = dict(current)
        for key, value in incoming.items():
            merged[key] = merge_missing(current.get(key), value) if key in current else value
        return merged
    return current


@card_import_router.post('/{resource_id}/import-card', response_model=CardImportResponse)
async def import_character_card(resource_id: str,
                                user: AuthenticatedUserDependency,
                                database: DatabaseDependency,
                                storage: StorageDependency,
                                file: UploadFile = File(...),
                                ) -> CardImportResponse:
    resource = await get_editable_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_CHARACTER,
    )
    payload = await file.read(CONFIG.image_max_bytes + 1)
    if len(payload) > CONFIG.image_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 'Card file is too large')

    suffix = Path(file.filename or '').suffix.casefold()
    try:
        if suffix == '.json':
            imported = parse_card_json(payload)
        elif suffix == '.png':
            imported = extract_card_from_png(payload)
        else:
            raise ValueError('Only JSON and PNG character cards are supported')
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    existing = (
        await database.silly_tavern_character_data.get(resource.draft_data_id)
        if resource.draft_data_id else None
    )
    current_data = existing.data.model_dump() if existing else {}
    imported_data = imported.model_dump()
    merged_payload = merge_missing(current_data, imported_data)

    imported_description = imported_data.get('description', '')
    imported_tags = imported_data.get('tags', [])
    merged_payload.update({'description': '', 'tags': [], 'creator': ''})
    try:
        merged_data = SillyTavernCharacterData.model_validate(merged_payload)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Imported card could not be merged into the current V3 draft',
        ) from error

    cover_image_id = resource.cover_image_resource_id
    if suffix == '.png':
        cover = await create_image_resource(
            name=f'Cover image for {resource.metadata.name}',
            description='',
            visibility=resource.metadata.visibility,
            tags=[],
            source=payload,
            user=user,
            database=database,
            storage=storage,
        )
        cover_image_id = cover.id

    if existing:
        draft = await database.silly_tavern_character_data.update(existing.model_copy(update={
            'data': merged_data,
            'updated_at': utc_now(),
        }))
    else:
        draft = await database.silly_tavern_character_data.create(
            SillyTavernCharacterDataDocument(resourceId=resource.id, data=merged_data),
        )

    merged_tags = list(resource.metadata.tags)
    merged_tags.extend(tag for tag in imported_tags if tag not in merged_tags)
    updated_resource = await database.resource.update(resource.model_copy(update={
        'draft_data_id': draft.id,
        'cover_image_resource_id': cover_image_id,
        'metadata': ResourceMetadata(
            name=resource.metadata.name,
            description=resource.metadata.description or imported_description,
            language=resource.metadata.language,
            visibility=resource.metadata.visibility,
            tags=tuple(merged_tags),
        ),
        'updated_at': utc_now(),
    }))
    return CardImportResponse(resource=updated_resource, draft=draft)


@card_import_router.post('/{resource_id}/import-lorebook', response_model=LorebookImportResponse)
async def import_lorebook(resource_id: str,
                          user: AuthenticatedUserDependency,
                          database: DatabaseDependency,
                          file: UploadFile = File(...),
                          ) -> LorebookImportResponse:
    resource = await get_editable_resource(
        database, resource_id, user, ResourceType.SILLY_TAVERN_LOREBOOK,
    )
    payload = await file.read(CONFIG.image_max_bytes + 1)
    if len(payload) > CONFIG.image_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 'Lorebook file is too large')

    suffix = Path(file.filename or '').suffix.casefold()
    try:
        if suffix == '.json':
            imported = parse_lorebook_json(payload)
        elif suffix == '.png':
            imported = extract_lorebook_from_png(payload)
        else:
            raise ValueError('Only JSON lorebooks and JSON/PNG character cards are supported')
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    existing = (
        await database.silly_tavern_lorebook_data.get(resource.draft_data_id)
        if resource.draft_data_id else None
    )
    current_data = existing.data.model_dump() if existing else {}
    imported_data = imported.model_dump()
    merged_payload = merge_missing(current_data, imported_data)
    imported_description = imported.description or ''
    merged_payload.update({'name': None, 'description': None})
    try:
        merged_data = SillyTavernCardV3LoreBook.model_validate(merged_payload)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Imported lorebook could not be merged into the current V3 draft',
        ) from error

    if existing:
        draft = await database.silly_tavern_lorebook_data.update(existing.model_copy(update={
            'data': merged_data,
            'updated_at': utc_now(),
        }))
    else:
        draft = await database.silly_tavern_lorebook_data.create(
            SillyTavernLorebookDataDocument(resourceId=resource.id, data=merged_data),
        )
    updated_resource = await database.resource.update(resource.model_copy(update={
        'draft_data_id': draft.id,
        'metadata': ResourceMetadata(
            name=resource.metadata.name,
            description=resource.metadata.description or imported_description,
            language=resource.metadata.language,
            visibility=resource.metadata.visibility,
            tags=resource.metadata.tags,
        ),
        'updated_at': utc_now(),
    }))
    return LorebookImportResponse(resource=updated_resource, draft=draft)
