from difflib import unified_diff

from pydantic import BaseModel


def render_release_text(payload: BaseModel | None) -> str | None:
    """Render a release payload as deterministic, indented JSON text for diffing."""
    if payload is None:
        return None
    return payload.model_dump_json(by_alias=True, exclude_none=True, indent=2) + '\n'


def build_content_diff(previous_text: str | None, current_text: str | None) -> str | None:
    """Unified diff of current_text against previous_text.

    A null previous_text (no prior release) is treated as an empty document, so the first
    release's diff is the whole document as additions, the same way git diffs an initial commit.
    Returns None when there is no current text to diff (non-textual resource types).
    """
    if current_text is None:
        return None
    previous_lines = (previous_text or '').splitlines(keepends=True)
    current_lines = current_text.splitlines(keepends=True)
    return ''.join(unified_diff(
        previous_lines, current_lines,
        fromfile='previous-release', tofile='this-release',
    ))
