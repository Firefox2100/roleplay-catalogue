from base64 import b64encode
from io import BytesIO
from json import dumps

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from roleplay_catalogue.routers.card_imports import (
    extract_card_from_png,
    extract_lorebook_from_png,
    merge_missing,
    parse_card_json,
    parse_lorebook_json,
)


def card_payload(spec: str = 'chara_card_v3') -> dict:
    version = '3.0' if spec == 'chara_card_v3' else '2.0'
    return {
        'spec': spec,
        'spec_version': version,
        'data': {
            'name': 'Imported character',
            'description': 'Imported description',
            'first_mes': 'Hello',
            'alternate_greetings': ['Hi', 'Hello again'],
            'tags': ['imported'],
        },
    }


def test_v2_and_v3_json_are_normalised_to_v3_data() -> None:
    v2 = parse_card_json(dumps(card_payload('chara_card_v2')).encode())
    v3 = parse_card_json(dumps(card_payload()).encode())

    assert v2.name == v3.name == 'Imported character'
    assert v2.first_mes == v3.first_mes == 'Hello'


def test_png_card_is_extracted_from_v2_or_v3_text_fields() -> None:
    for field, spec in (('chara', 'chara_card_v2'), ('ccv3', 'chara_card_v3')):
        metadata = PngInfo()
        metadata.add_text(field, b64encode(dumps(card_payload(spec)).encode()).decode())
        png = BytesIO()
        Image.new('RGB', (4, 4), 'purple').save(png, format='PNG', pnginfo=metadata)

        assert extract_card_from_png(png.getvalue()).name == 'Imported character'


def test_merge_fills_blanks_and_appends_only_exactly_new_list_items() -> None:
    current = {
        'name': 'Existing',
        'first_mes': '',
        'alternate_greetings': ['Same', {'text': 'structured'}],
        'character_book': {'entries': [{'keys': ['one'], 'content': 'Existing'}]},
    }
    incoming = {
        'name': 'Imported',
        'first_mes': 'Imported greeting',
        'alternate_greetings': ['Same', 'New', {'text': 'structured'}],
        'character_book': {'entries': [
            {'keys': ['one'], 'content': 'Existing'},
            {'keys': ['two'], 'content': 'New'},
        ]},
    }

    merged = merge_missing(current, incoming)

    assert merged['name'] == 'Existing'
    assert merged['first_mes'] == 'Imported greeting'
    assert merged['alternate_greetings'] == ['Same', {'text': 'structured'}, 'New']
    assert merged['character_book']['entries'][-1]['content'] == 'New'


def lorebook_payload() -> dict:
    return {
        'spec': 'lorebook_v3',
        'data': {
            'name': 'Imported lore',
            'description': 'World background',
            'extensions': {},
            'entries': [{
                'keys': ['kingdom'],
                'content': 'A distant kingdom.',
                'extensions': {},
                'enabled': True,
                'insertion_order': 10,
                'use_regex': False,
                'constant': False,
            }],
        },
    }


def test_lorebook_json_identifier_distinguishes_standalone_and_character_card() -> None:
    standalone = parse_lorebook_json(dumps(lorebook_payload()).encode())
    character = card_payload()
    character['data']['character_book'] = lorebook_payload()['data']
    embedded = parse_lorebook_json(dumps(character).encode())

    assert standalone.entries[0].content == 'A distant kingdom.'
    assert embedded.entries == standalone.entries


def test_lorebook_is_extracted_from_png_character_without_using_image_data() -> None:
    character = card_payload()
    character['data']['character_book'] = lorebook_payload()['data']
    metadata = PngInfo()
    metadata.add_text('ccv3', b64encode(dumps(character).encode()).decode())
    png = BytesIO()
    Image.new('RGB', (4, 4), 'orange').save(png, format='PNG', pnginfo=metadata)

    lorebook = extract_lorebook_from_png(png.getvalue())

    assert lorebook.name == 'Imported lore'
    assert lorebook.entries[0].keys == ['kingdom']
