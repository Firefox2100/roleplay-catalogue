from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from roleplay_catalogue.components import AccountComponent, AuthComponent
from roleplay_catalogue.misc import UserCredentialMismatch
from roleplay_catalogue.models import User
from roleplay_catalogue.services import DatabaseService, MailingService, StorageService


def get_auth_component(request: Request) -> AuthComponent:
    return request.app.state.auth_component


def get_database_service(request: Request) -> DatabaseService:
    return request.app.state.database_service


def get_mailing_service(request: Request) -> MailingService:
    return request.app.state.mailing_service


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service


def get_account_component(request: Request) -> AccountComponent:
    return request.app.state.account_component


AuthDependency = Annotated[
    AuthComponent,
    Depends(get_auth_component),
]


DatabaseDependency = Annotated[
    DatabaseService,
    Depends(get_database_service)
]


MailingDependency = Annotated[
    MailingService,
    Depends(get_mailing_service),
]


StorageDependency = Annotated[
    StorageService,
    Depends(get_storage_service),
]


AccountDependency = Annotated[
    AccountComponent,
    Depends(get_account_component),
]


api_key_bearer = HTTPBearer(auto_error=False)


async def authenticate_user(request: Request,
                            database: DatabaseDependency,
                            auth: AuthDependency,
                            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_bearer)],
                            ) -> User:
    if credentials and credentials.scheme.casefold() == 'bearer':
        try:
            return await auth.authenticate_api_key(credentials.credentials)
        except UserCredentialMismatch as error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                'Invalid or expired API key',
                headers={'WWW-Authenticate': 'Bearer'},
            ) from error

    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required',
        )

    user = await database.user.get(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required',
        )

    return user


AuthenticatedUserDependency = Annotated[
    User,
    Depends(authenticate_user),
]


async def authenticate_session_user(request: Request,
                                    database: DatabaseDependency,
                                    ) -> User:
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Authentication required')
    user = await database.user.get(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Authentication required')
    return user


SessionAuthenticatedUserDependency = Annotated[
    User,
    Depends(authenticate_session_user),
]


async def optionally_authenticate_user(request: Request,
                                       database: DatabaseDependency,
                                       auth: AuthDependency,
                                       credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_bearer)],
                                       ) -> User | None:
    if credentials and credentials.scheme.casefold() == 'bearer':
        try:
            return await auth.authenticate_api_key(credentials.credentials)
        except UserCredentialMismatch as error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                'Invalid or expired API key',
                headers={'WWW-Authenticate': 'Bearer'},
            ) from error

    user_id = request.session.get('user_id')
    if not user_id:
        return None

    user = await database.user.get(user_id)
    if not user:
        request.session.clear()
    return user


OptionalAuthenticatedUserDependency = Annotated[
    User | None,
    Depends(optionally_authenticate_user),
]


async def authenticate_api_key(
        auth: AuthDependency,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_bearer)],
        ) -> User:
    if not credentials or credentials.scheme.casefold() != 'bearer':
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            'API key authentication required',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    try:
        return await auth.authenticate_api_key(credentials.credentials)
    except UserCredentialMismatch as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            'Invalid or expired API key',
            headers={'WWW-Authenticate': 'Bearer'},
        ) from error


ApiKeyAuthenticatedUserDependency = Annotated[
    User,
    Depends(authenticate_api_key),
]
