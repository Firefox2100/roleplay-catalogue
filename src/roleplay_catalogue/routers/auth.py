from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import Field

from roleplay_catalogue.misc import (
    InvalidActivationToken,
    UserAlreadyExists,
    UserCredentialMismatch,
    UserNotFound,
    UserRole,
    UserStatus,
)
from roleplay_catalogue.models import CommonModel
from roleplay_catalogue.middleware import CSRF_SESSION_KEY
from .utils import AuthDependency, AuthenticatedUserDependency


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
