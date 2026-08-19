from pydantic import BaseModel

from roleplay_catalogue.components import build_content_diff, render_release_text


class Payload(BaseModel):
    name: str
    tags: list[str] = []


def test_render_release_text_returns_none_for_missing_payload() -> None:
    assert render_release_text(None) is None


def test_render_release_text_is_deterministic_indented_json() -> None:
    text = render_release_text(Payload(name='Example', tags=['a', 'b']))

    assert text == '{\n  "name": "Example",\n  "tags": [\n    "a",\n    "b"\n  ]\n}\n'


def test_first_release_diff_is_a_full_creation_against_an_empty_document() -> None:
    diff = build_content_diff(None, render_release_text(Payload(name='Example')))

    assert diff is not None
    lines = diff.splitlines()
    added_lines = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
    removed_lines = [line for line in lines if line.startswith('-') and not line.startswith('---')]
    assert removed_lines == []
    assert any('"name": "Example"' in line for line in added_lines)

    empty_previous_diff = build_content_diff('', render_release_text(Payload(name='Example')))
    assert empty_previous_diff == diff


def test_diff_reflects_only_the_change_between_releases() -> None:
    previous_text = render_release_text(Payload(name='Original'))
    current_text = render_release_text(Payload(name='Renamed'))

    diff = build_content_diff(previous_text, current_text)

    assert '-  "name": "Original"' in diff
    assert '+  "name": "Renamed"' in diff


def test_diff_is_none_for_resource_types_without_textual_content() -> None:
    assert build_content_diff(None, None) is None
