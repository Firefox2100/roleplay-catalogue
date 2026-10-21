"""Docker-backed MongoDB, SeaweedFS, Redis, and Mailpit fixtures."""

import uuid

import aioboto3
import httpx
import pytest
from aiosmtplib import SMTP
from botocore.config import Config
from jinja2 import DictLoader, Environment, select_autoescape
from pymongo import AsyncMongoClient
from redis.asyncio import Redis
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HealthcheckWaitStrategy, LogMessageWaitStrategy

from roleplay_catalogue.services import CacheService, DatabaseService, MailingService, StorageService


def _docker_available() -> bool:
    try:
        import docker
        docker.from_env().ping()
    except Exception:
        return False
    return True


@pytest.fixture(scope='session')
def _require_docker() -> None:
    if not _docker_available():
        pytest.skip('Docker is not reachable; skipping the integration test tier')


# MongoDB Atlas Local: self-initializes a single-node replica set, matches production's
# mongod+mongot pairing.

@pytest.fixture(scope='session')
def mongodb_url(_require_docker) -> str:
    container = DockerContainer('mongodb/mongodb-atlas-local:latest')
    container.with_exposed_ports(27017)
    container.waiting_for(HealthcheckWaitStrategy().with_startup_timeout(90))
    container.start()
    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(27017)
        yield f'mongodb://{host}:{port}/?directConnection=true'
    finally:
        container.stop()


@pytest.fixture(scope='session')
async def mongo_client(mongodb_url: str):
    client = AsyncMongoClient(mongodb_url, tz_aware=True)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture(scope='session')
async def mongo_database(mongo_client):
    database_name = f'rc_test_{uuid.uuid4().hex}'
    try:
        yield mongo_client[database_name]
    finally:
        await mongo_client.drop_database(database_name)


async def _clear_mongo_documents(database) -> None:
    for collection_name in await database.list_collection_names():
        await database[collection_name].delete_many({})


@pytest.fixture(autouse=True)
async def _isolate_mongo_test_data(mongo_database):
    await _clear_mongo_documents(mongo_database)
    yield
    await _clear_mongo_documents(mongo_database)


@pytest.fixture(scope='session')
async def database_service(mongo_database):
    service = DatabaseService(client=mongo_database.client, database_name=mongo_database.name)
    await service.initialize()
    yield service


# Redis: authoritative store for short-lived activation and password-reset credentials.

@pytest.fixture(scope='session')
def redis_url(_require_docker) -> str:
    container = DockerContainer('redis:8-alpine')
    container.with_exposed_ports(6379)
    container.waiting_for(LogMessageWaitStrategy('Ready to accept connections').with_startup_timeout(30))
    container.start()
    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6379)
        yield f'redis://{host}:{port}/0'
    finally:
        container.stop()


@pytest.fixture
async def cache_service(redis_url: str):
    client = Redis.from_url(redis_url, decode_responses=True)
    service = CacheService(client, 'rc-test')
    await service.initialize()
    try:
        await client.flushdb()
        yield service
    finally:
        await client.flushdb()
        await service.close()


# SeaweedFS: S3-compatible storage backend, matching compose.yaml

S3_ACCESS_KEY = 'integration-test'
S3_SECRET_KEY = 'integration-test-secret'
SEAWEEDFS_IMAGE = 'chrislusf/seaweedfs:4.48'


@pytest.fixture(scope='session')
def seaweedfs_endpoint(_require_docker) -> str:
    container = DockerContainer(SEAWEEDFS_IMAGE)
    container.with_command('mini -dir=/data -master.telemetry=false')
    container.with_env('AWS_ACCESS_KEY_ID', S3_ACCESS_KEY)
    container.with_env('AWS_SECRET_ACCESS_KEY', S3_SECRET_KEY)
    container.with_exposed_ports(8333)
    container.waiting_for(
        LogMessageWaitStrategy('Start Seaweed S3 API Server').with_startup_timeout(30)
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8333)
        yield f'http://{host}:{port}'
    finally:
        container.stop()


@pytest.fixture
async def storage_service(seaweedfs_endpoint: str):
    bucket = f'rc-test-{uuid.uuid4().hex}'
    session = aioboto3.Session()
    async with session.client(
            's3',
            endpoint_url=seaweedfs_endpoint,
            region_name='us-east-1',
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=Config(signature_version='s3v4'),
    ) as client:
        await client.create_bucket(Bucket=bucket)
        yield StorageService(client, bucket, signed_url_expiry=60)


# Mailpit: disposable SMTP catcher with a REST API to inspect what was delivered

@pytest.fixture(scope='session')
def mailpit_endpoints(_require_docker) -> tuple[str, int, int]:
    container = DockerContainer('axllent/mailpit')
    container.with_exposed_ports(1025, 8025)
    container.waiting_for(LogMessageWaitStrategy('accessible via').with_startup_timeout(30))
    container.start()
    try:
        host = container.get_container_host_ip()
        smtp_port = container.get_exposed_port(1025)
        api_port = container.get_exposed_port(8025)
        yield host, smtp_port, api_port
    finally:
        container.stop()


@pytest.fixture
async def mailpit(mailpit_endpoints: tuple[str, int, int]):
    host, smtp_port, api_port = mailpit_endpoints
    api_url = f'http://{host}:{api_port}'
    async with httpx.AsyncClient() as http:
        await http.delete(f'{api_url}/api/v1/messages')

    client = SMTP(hostname=host, port=smtp_port, use_tls=False, start_tls=False)
    await client.connect()
    try:
        service = MailingService(
            client=client,
            sender='integration-tests@example.com',
            template_environment=Environment(
                loader=DictLoader({}), autoescape=select_autoescape(['html']),
            ),
        )
        yield service, api_url
    finally:
        client.close()
