from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.services import DatabaseService
from roleplay_catalogue.components import AuthComponent
from roleplay_catalogue.routers import auth_router
from roleplay_catalogue.middleware import CSRFMiddleware


@asynccontextmanager
async def lifespan(application: FastAPI):
    mongo_client = AsyncMongoClient(
        host=CONFIG.mongodb_host,
        port=CONFIG.mongodb_port,
    )
    database_service = DatabaseService(
        client=mongo_client,
        database_name=CONFIG.mongodb_name,
    )

    auth_component = AuthComponent(
        database=database_service,
    )

    app.state.database_service = database_service
    app.state.auth_component = auth_component

    try:
        yield
    finally:
        await database_service.close()


app = FastAPI(
    lifespan=lifespan,
)

app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=CONFIG.session_secret,
    session_cookie=CONFIG.session_cookie_name,
    max_age=CONFIG.session_max_age,
    same_site='lax',
    https_only=CONFIG.session_cookie_secure,
)

app.include_router(auth_router)
