from contextlib import asynccontextmanager
import logging
import aioboto3
from aiosmtplib import SMTP
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from roleplay_catalogue.misc import CONFIG
from roleplay_catalogue.services import DatabaseService, MailingService, StorageService
from roleplay_catalogue.components import AccountComponent, AuthComponent
from roleplay_catalogue.routers import (
    auth_router,
    card_import_router,
    image_data_router,
    image_router,
    resource_router,
    resource_version_router,
    world_router,
    preset_router,
)
from roleplay_catalogue.middleware import CSRFMiddleware, SecurityHeadersMiddleware


LOGGER = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404:
                raise
            return await super().get_response('index.html', scope)


@asynccontextmanager
async def lifespan(application: FastAPI):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    mongo_client = AsyncMongoClient(
        host=CONFIG.mongodb_host,
        port=CONFIG.mongodb_port,
        tz_aware=True,
        directConnection=CONFIG.mongodb_direct_connection,
        replicaSet=CONFIG.mongodb_replica_set,
        username=CONFIG.mongodb_username,
        password=CONFIG.mongodb_password,
        authSource=CONFIG.mongodb_name if CONFIG.mongodb_username else None,
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
        storage_service = StorageService(
            storage_client,
            CONFIG.s3_bucket,
            CONFIG.s3_signed_url_expiry,
        )
        auth_component = AuthComponent(
            database=database_service,
            mailing=mailing_service,
            public_base_url=CONFIG.public_base_url,
            activation_token_max_age=CONFIG.activation_token_max_age,
            password_reset_token_max_age=CONFIG.password_reset_token_max_age,
        )
        account_component = AccountComponent(
            database_service, storage_service, CONFIG.pending_account_retention,
        )
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            account_component.purge_expired_pending_accounts,
            'interval',
            seconds=CONFIG.account_cleanup_interval,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            auth_component.purge_expired_api_keys,
            'interval',
            seconds=CONFIG.api_key_cleanup_interval,
            max_instances=1,
            coalesce=True,
        )
        scheduler_started = False

        application.state.database_service = database_service
        application.state.mailing_service = mailing_service
        application.state.storage_service = storage_service
        application.state.auth_component = auth_component
        application.state.account_component = account_component

        try:
            await database_service.initialize()
            for problem in await database_service.check_integrity():
                LOGGER.warning('Database integrity check: %s', problem)
            await smtp_client.connect()
            scheduler.start()
            scheduler_started = True
            yield
        finally:
            if scheduler_started:
                scheduler.shutdown(wait=False)
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
if CONFIG.security_headers_enabled:
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy=CONFIG.content_security_policy,
        hsts_max_age=CONFIG.hsts_max_age,
        hsts_include_subdomains=CONFIG.hsts_include_subdomains,
        hsts_preload=CONFIG.hsts_preload,
    )
app.add_middleware(
    SessionMiddleware,
    secret_key=CONFIG.session_secret,
    session_cookie=CONFIG.session_cookie_name,
    max_age=CONFIG.session_max_age,
    same_site='lax',
    https_only=CONFIG.session_cookie_secure,
)

for router in (
    auth_router, card_import_router, resource_router, resource_version_router,
    image_data_router, image_router,
    world_router,
    preset_router,
):
    app.include_router(router, prefix=CONFIG.api_prefix)

if CONFIG.frontend_dist_path is not None:
    app.mount('/', SPAStaticFiles(directory=CONFIG.frontend_dist_path, html=True), name='frontend')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        app,
        host=CONFIG.app_host,
        port=CONFIG.app_port,
    )
