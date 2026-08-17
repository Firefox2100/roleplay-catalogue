from contextvars import ContextVar

from pymongo.asynchronous.client_session import AsyncClientSession


CURRENT_SESSION: ContextVar[AsyncClientSession | None] = ContextVar(
    'roleplay_catalogue_database_session', default=None,
)


def current_session() -> AsyncClientSession | None:
    return CURRENT_SESSION.get()
