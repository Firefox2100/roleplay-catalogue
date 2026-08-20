from typing import Any, NoReturn

from fastapi import HTTPException, status


def parse_if_match(if_match: str | None) -> int:
    """Extract the expected revision number from an If-Match header value."""
    if if_match is None:
        raise HTTPException(
            status.HTTP_428_PRECONDITION_REQUIRED,
            'An If-Match header carrying the current ETag is required for this write',
        )
    try:
        return int(if_match.strip().strip('"'))
    except ValueError as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'If-Match header must be a quoted revision number',
        ) from error


def etag_header(revision: int) -> str:
    return f'"{revision}"'


def raise_stale_revision(current: Any) -> NoReturn:
    """Raise 412 with the current document embedded, so the client can merge without a refetch."""
    raise HTTPException(
        status.HTTP_412_PRECONDITION_FAILED,
        detail={
            'message': 'This was modified since it was last loaded',
            'current': current.model_dump(mode='json', by_alias=True),
        },
        headers={'ETag': etag_header(current.revision)},
    )
