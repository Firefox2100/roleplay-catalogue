from typing import Annotated
from fastapi import Depends, HTTPException, Request, status

from roleplay_catalogue.components import AuthComponent
from roleplay_catalogue.models import User
from roleplay_catalogue.services import DatabaseService


def get_auth_component(request: Request) -> AuthComponent:
    return request.app.state.auth_component


def get_database_service(request: Request) -> DatabaseService:
    return request.app.state.database_service


AuthDependency = Annotated[
    AuthComponent,
    Depends(get_auth_component),
]


DatabaseDependency = Annotated[
    DatabaseService,
    Depends(get_database_service)
]


async def authenticate_user(request: Request,
                            database: DatabaseDependency,
                            ) -> User:
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
