from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from roleplay_catalogue.main import app
from roleplay_catalogue.misc import UserCredentialMismatch
from roleplay_catalogue.models import User
from roleplay_catalogue.routers.utils import (
    authenticate_user,
    get_auth_component,
    get_database_service,
)


USER = User(
    id='user-id',
    username='alice',
    email='alice@example.com',
    passwordHash='hash',
)


class FakeAuthComponent:
    async def authenticate_user(self,
                                username: str,
                                password: str,
                                ) -> User:
        if username != 'alice' or password != 'correct-password':
            raise UserCredentialMismatch('Invalid credentials')
        return USER

    async def register_user(self,
                            username: str,
                            email: str,
                            password: str,
                            ) -> User:
        return USER

    async def activate_user(self,
                            username: str,
                            token: str,
                            ) -> User:
        return USER


class FakeUserRepository:
    async def get(self, user_id: str) -> User | None:
        return USER if user_id == USER.id else None


class FakeDatabaseService:
    user = FakeUserRepository()


@app.get('/authenticated-user-test', include_in_schema=False)
async def authenticated_user_test(user: User = Depends(authenticate_user)) -> dict[str, str]:
    return {'id': user.id}


def get_client() -> AsyncClient:
    app.dependency_overrides[get_auth_component] = FakeAuthComponent
    app.dependency_overrides[get_database_service] = FakeDatabaseService
    return AsyncClient(transport=ASGITransport(app=app), base_url='http://test')


async def test_login_sets_session_and_logout_clears_it() -> None:
    async with get_client() as client:
        csrf_response = await client.get('/auth/csrf')
        csrf_token = csrf_response.json()['csrfToken']

        response = await client.post(
            '/auth/login',
            headers={'X-CSRF-Token': csrf_token},
            json={'username': 'alice', 'password': 'correct-password'},
        )

        assert response.status_code == 204
        assert 'roleplay_catalogue_session' in client.cookies
        assert (await client.get('/authenticated-user-test')).json() == {'id': USER.id}
        current_user = await client.get('/auth/me')
        assert current_user.status_code == 200
        assert current_user.json()['username'] == USER.username
        assert 'passwordHash' not in current_user.json()

        csrf_token = (await client.get('/auth/csrf')).json()['csrfToken']
        response = await client.post('/auth/logout', headers={'X-CSRF-Token': csrf_token})

        assert response.status_code == 204
        assert 'roleplay_catalogue_session' not in client.cookies
        assert (await client.get('/authenticated-user-test')).status_code == 401


async def test_state_changing_requests_require_csrf_token() -> None:
    async with get_client() as client:
        response = await client.post(
            '/auth/login',
            json={'username': 'alice', 'password': 'correct-password'},
        )
        assert response.status_code == 403


async def test_invalid_credentials_do_not_create_authenticated_session() -> None:
    async with get_client() as client:
        csrf_token = (await client.get('/auth/csrf')).json()['csrfToken']
        response = await client.post(
            '/auth/login',
            headers={'X-CSRF-Token': csrf_token},
            json={'username': 'alice', 'password': 'wrong-password'},
        )

        assert response.status_code == 401
        assert (await client.get('/authenticated-user-test')).status_code == 401


async def test_registration_and_activation_endpoints() -> None:
    async with get_client() as client:
        csrf_token = (await client.get('/auth/csrf')).json()['csrfToken']
        response = await client.post(
            '/auth/register',
            headers={'X-CSRF-Token': csrf_token},
            json={
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'correct-password',
            },
        )
        assert response.status_code == 202

        response = await client.get(
            '/auth/activation',
            params={'username': 'alice', 'token': 'activation-token'},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers['location'] == '/login?activation=success'
