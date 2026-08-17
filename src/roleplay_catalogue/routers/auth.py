from datetime import datetime, timedelta
from enum import StrEnum
from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import Field

from roleplay_catalogue.misc import (
    InvalidActivationToken,
    InvalidPasswordResetToken,
    UserAlreadyExists,
    UserCredentialMismatch,
    UserNotFound,
    UserRole,
    UserStatus,
)
from roleplay_catalogue.models import CommonModel
from roleplay_catalogue.middleware import CSRF_SESSION_KEY
from .utils import AccountDependency, AuthDependency, AuthenticatedUserDependency


auth_router = APIRouter(
    prefix='/auth',
    tags=['Authentication'],
)


class LoginRequest(CommonModel):
    username: str = Field(..., description='Username')
    password: str = Field(..., description='Password')


class RegistrationRequest(CommonModel):
    username: str = Field(..., min_length=1, max_length=100, description='Username')
    email: str = Field(..., min_length=3, max_length=320, description='Email address')
    password: str = Field(..., min_length=8, max_length=1024, description='Password')


class CurrentUserResponse(CommonModel):
    id: str
    username: str
    email: str
    role: UserRole
    status: UserStatus


class PasswordResetRequest(CommonModel):
    email: str = Field(..., min_length=3, max_length=320)


class PasswordResetConfirmRequest(CommonModel):
    user_id: str = Field(..., alias='userId')
    token: str = Field(..., min_length=1, max_length=1024)
    new_password: str = Field(..., min_length=8, max_length=1024, alias='newPassword')


class PasswordChangeRequest(CommonModel):
    current_password: str = Field(..., min_length=1, max_length=1024, alias='currentPassword')
    new_password: str = Field(..., min_length=8, max_length=1024, alias='newPassword')


class AccountDeleteRequest(CommonModel):
    password: str = Field(..., min_length=1, max_length=1024)


class ApiKeyLifetime(StrEnum):
    ONE_WEEK = 'oneWeek'
    ONE_MONTH = 'oneMonth'
    SIX_MONTHS = 'sixMonths'
    ONE_YEAR = 'oneYear'
    NEVER = 'never'


API_KEY_LIFETIMES = {
    ApiKeyLifetime.ONE_WEEK: timedelta(days=7),
    ApiKeyLifetime.ONE_MONTH: timedelta(days=30),
    ApiKeyLifetime.SIX_MONTHS: timedelta(days=182),
    ApiKeyLifetime.ONE_YEAR: timedelta(days=365),
    ApiKeyLifetime.NEVER: None,
}


class ApiKeyCreateRequest(CommonModel):
    name: str = Field(..., min_length=1, max_length=100)
    lifetime: ApiKeyLifetime


class ApiKeyResponse(CommonModel):
    id: str
    name: str
    created_at: datetime = Field(..., alias='createdAt')
    expires_at: datetime | None = Field(None, alias='expiresAt')


class CreatedApiKeyResponse(ApiKeyResponse):
    key: str


@auth_router.post('/login')
async def login_user(login_request: LoginRequest,
                     auth: AuthDependency,
                     request: Request,
                     response: Response,
                     ) -> None:
    try:
        user = await auth.authenticate_user(
            username=login_request.username,
            password=login_request.password
        )
    except (UserNotFound, UserCredentialMismatch) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid username or password',
        ) from error

    request.session.clear()
    request.session['user_id'] = user.id
    request.session[CSRF_SESSION_KEY] = token_urlsafe(32)
    response.status_code = status.HTTP_204_NO_CONTENT


@auth_router.get('/csrf')
async def get_csrf_token(request: Request) -> dict[str, str]:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token

    return {'csrfToken': token}


@auth_router.get('/me', response_model=CurrentUserResponse)
async def get_current_user(user: AuthenticatedUserDependency) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(user.model_dump())


@auth_router.post('/register', status_code=status.HTTP_202_ACCEPTED)
async def register_user(registration_request: RegistrationRequest,
                        auth: AuthDependency,
                        ) -> None:
    try:
        await auth.register_user(
            username=registration_request.username,
            email=registration_request.email,
            password=registration_request.password,
        )
    except UserAlreadyExists as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Username or email address is already registered',
        ) from error


@auth_router.get('/activation', response_class=RedirectResponse)
async def activate_user(username: str,
                        token: str,
                        auth: AuthDependency,
                        ) -> RedirectResponse:
    try:
        await auth.activate_user(username=username, token=token)
    except InvalidActivationToken:
        return RedirectResponse(
            url='/login?activation=invalid',
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url='/login?activation=success',
        status_code=status.HTTP_303_SEE_OTHER,
    )


@auth_router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(request: Request) -> None:
    request.session.clear()


@auth_router.post('/password-reset/request', status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(payload: PasswordResetRequest,
                                 auth: AuthDependency) -> None:
    await auth.request_password_reset(payload.email)


@auth_router.post('/password-reset/confirm', status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(payload: PasswordResetConfirmRequest,
                                 auth: AuthDependency) -> None:
    try:
        await auth.reset_password(payload.user_id, payload.token, payload.new_password)
    except InvalidPasswordResetToken as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@auth_router.post('/password', status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: PasswordChangeRequest,
                          user: AuthenticatedUserDependency,
                          auth: AuthDependency) -> None:
    try:
        await auth.change_password(user, payload.current_password, payload.new_password)
    except UserCredentialMismatch as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Current password is incorrect') from error


@auth_router.get('/api-keys', response_model=list[ApiKeyResponse])
async def list_api_keys(user: AuthenticatedUserDependency,
                        auth: AuthDependency) -> list[ApiKeyResponse]:
    keys = await auth.list_api_keys(user)
    return [ApiKeyResponse.model_validate(key.model_dump()) for key in keys]


@auth_router.post('/api-keys', response_model=CreatedApiKeyResponse,
                  status_code=status.HTTP_201_CREATED)
async def create_api_key(payload: ApiKeyCreateRequest,
                         user: AuthenticatedUserDependency,
                         auth: AuthDependency) -> CreatedApiKeyResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'API key name must not be blank')
    api_key, secret = await auth.create_api_key(user, name, API_KEY_LIFETIMES[payload.lifetime])
    return CreatedApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        createdAt=api_key.created_at,
        expiresAt=api_key.expires_at,
        key=secret,
    )


@auth_router.delete('/api-keys/{key_id}', status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str,
                         user: AuthenticatedUserDependency,
                         auth: AuthDependency) -> None:
    if not await auth.revoke_api_key(user, key_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'API key not found')


@auth_router.delete('/account', status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(payload: AccountDeleteRequest,
                         request: Request,
                         user: AuthenticatedUserDependency,
                         auth: AuthDependency,
                         accounts: AccountDependency) -> None:
    try:
        auth.verify_password(user, payload.password)
    except UserCredentialMismatch as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Current password is incorrect') from error
    await accounts.delete_account(user)
    request.session.clear()
