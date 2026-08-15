from secrets import token_urlsafe

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import Field

from roleplay_catalogue.misc import UserCredentialMismatch, UserNotFound
from roleplay_catalogue.models import CommonModel
from roleplay_catalogue.middleware import CSRF_SESSION_KEY
from .utils import AuthDependency


auth_router = APIRouter(
    prefix='/auth',
    tags=['Authentication'],
)


class LoginRequest(CommonModel):
    username: str = Field(..., description='Username')
    password: str = Field(..., description='Password')


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


@auth_router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(request: Request) -> None:
    request.session.clear()
