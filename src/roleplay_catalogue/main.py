from contextlib import asynccontextmanager
import aioboto3
from aiosmtplib import SMTP
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from starlette.middleware.sessions import SessionMiddleware

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.services import DatabaseService, MailingService, StorageService
from roleplay_catalogue.components import AuthComponent
from roleplay_catalogue.routers import (
    auth_router,
    image_data_router,
    image_router,
    resource_router,
    resource_version_router,
    silly_tavern_character_data_router,
    silly_tavern_lorebook_data_router,
)
from roleplay_catalogue.middleware import CSRFMiddleware


@asynccontextmanager
async def lifespan(application: FastAPI):
    mongo_client = AsyncMongoClient(
        host=CONFIG.mongodb_host,
        port=CONFIG.mongodb_port,
        tz_aware=True,
        directConnection=CONFIG.mongodb_direct_connection,
    )
    database_service = DatabaseService(
        client=mongo_client,
        database_name=CONFIG.mongodb_name,
    )
    smtp_client = SMTP(
        hostname=CONFIG.smtp_host,
        port=CONFIG.smtp_port,
        username=CONFIG.smtp_username,
        password=CONFIG.smtp_password,
        use_tls=CONFIG.smtp_use_tls,
        start_tls=CONFIG.smtp_start_tls,
    )
    mailing_service = MailingService(
        client=smtp_client,
        sender=CONFIG.smtp_sender,
        template_environment=Environment(
            loader=PackageLoader('roleplay_catalogue', 'data/email_templates'),
            autoescape=select_autoescape(['html']),
        ),
    )

    session = aioboto3.Session()
    async with session.client(
            's3',
            endpoint_url=CONFIG.s3_endpoint_url,
            region_name=CONFIG.s3_region,
            aws_access_key_id=CONFIG.s3_access_key_id,
            aws_secret_access_key=CONFIG.s3_secret_access_key,
    ) as storage_client:
        storage_service = StorageService(storage_client, CONFIG.s3_bucket)
        auth_component = AuthComponent(
            database=database_service,
            mailing=mailing_service,
            public_base_url=CONFIG.public_base_url,
            activation_token_max_age=CONFIG.activation_token_max_age,
        )

        application.state.database_service = database_service
        application.state.mailing_service = mailing_service
        application.state.storage_service = storage_service
        application.state.auth_component = auth_component

        try:
            await database_service.initialize()
            await smtp_client.connect()
            yield
        finally:
            smtp_client.close()
            await database_service.close()


app = FastAPI(
    lifespan=lifespan,
)


@app.exception_handler(DuplicateKeyError)
async def duplicate_key_error_handler(_request: Request,
                                      _error: DuplicateKeyError,
                                      ) -> JSONResponse:
    return JSONResponse(
        {'detail': 'A resource with the same identity or version already exists'},
        status_code=409,
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
app.include_router(resource_router)
app.include_router(resource_version_router)
app.include_router(silly_tavern_character_data_router)
app.include_router(silly_tavern_lorebook_data_router)
app.include_router(image_data_router)
app.include_router(image_router)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=CONFIG.app_host,
        port=CONFIG.app_port,
    )
