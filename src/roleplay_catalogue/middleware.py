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

        headers = Headers(scope=scope)
        authorization = headers.get('authorization', '')
        uses_bearer_auth = authorization.partition(' ')[0].casefold() == 'bearer'
        if uses_bearer_auth and not scope['session'].get('user_id'):
            await self._app(scope, receive, send)
            return

        session_token = scope['session'].get(CSRF_SESSION_KEY)
        request_token = headers.get(CSRF_HEADER_NAME)

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


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, content_security_policy: str,
                 hsts_max_age: int = 0, hsts_include_subdomains: bool = False,
                 hsts_preload: bool = False):
        self._app = app
        self._headers = [
            (b'x-content-type-options', b'nosniff'),
            (b'referrer-policy', b'strict-origin-when-cross-origin'),
            (b'permissions-policy', b'camera=(), microphone=(), geolocation=()'),
            (b'content-security-policy', content_security_policy.encode('latin-1')),
        ]
        if hsts_max_age:
            value = f'max-age={hsts_max_age}'
            if hsts_include_subdomains:
                value += '; includeSubDomains'
            if hsts_preload:
                value += '; preload'
            self._headers.append((b'strict-transport-security', value.encode('ascii')))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message['type'] == 'http.response.start':
                existing = {name.lower() for name, _value in message['headers']}
                message['headers'].extend(
                    header for header in self._headers if header[0] not in existing
                )
            await send(message)

        await self._app(scope, receive, send_with_headers)
