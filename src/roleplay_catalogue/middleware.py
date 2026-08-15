from hmac import compare_digest
from typing import Final

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


CSRF_SESSION_KEY: Final = 'csrf_token'
CSRF_HEADER_NAME: Final = 'x-csrf-token'
SAFE_METHODS: Final = frozenset({'GET', 'HEAD', 'OPTIONS', 'TRACE'})


class CSRFMiddleware:
    def __init__(self,
                 app: ASGIApp,
                 ):
        self._app = app

    async def __call__(self,
                       scope: Scope,
                       receive: Receive,
                       send: Send,
                       ) -> None:
        if scope['type'] != 'http' or scope['method'] in SAFE_METHODS:
            await self._app(scope, receive, send)
            return

        session_token = scope['session'].get(CSRF_SESSION_KEY)
        request_token = Headers(scope=scope).get(CSRF_HEADER_NAME)

        if (not session_token or
                not request_token or
                not compare_digest(session_token, request_token)):
            response = JSONResponse(
                {'detail': 'Invalid or missing CSRF token'},
                status_code=403,
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)
