import pytest
from pydantic import ValidationError

from roleplay_catalogue.models import SillyTavernPresetData


def test_preset_preserves_provider_specific_settings() -> None:
    preset = SillyTavernPresetData.model_validate({
        'temperature': 0.7,
        'openrouter_model': 'example/model',
        'custom_include_body': '{"reasoning": true}',
        'prompts': [{'identifier': 'main', 'name': 'Main', 'role': 'system', 'content': 'Write.'}],
        'prompt_order': [{'character_id': 100000, 'order': [{'identifier': 'main', 'enabled': True}]}],
    })

    dumped = preset.model_dump()
    assert dumped['openrouter_model'] == 'example/model'
    assert dumped['custom_include_body'] == '{"reasoning": true}'
    assert dumped['prompts'][0]['identifier'] == 'main'


def test_preset_rejects_duplicate_prompt_identifiers() -> None:
    with pytest.raises(ValidationError, match='identifiers must be unique'):
        SillyTavernPresetData.model_validate({
            'prompts': [{'identifier': 'main'}, {'identifier': 'main'}],
        })
