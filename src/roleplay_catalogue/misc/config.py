import os
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='RC_',
        env_file_encoding='utf-8',
    )

    app_host: str = Field(
        '127.0.0.1',
        description='Host for the local server. Only relevant if using the start script.'
    )
    app_port: int = Field(
        9798,
        description='Port for the local server. Only relevant if using the start script.'
    )
    api_prefix: str = Field(
        '',
        pattern=r'^$|^/[^/]*$',
        description='Optional URL prefix for all API routes, for example /api.'
    )
    frontend_dist_path: Path | None = Field(
        None,
        description='Optional built frontend directory to serve with SPA fallback.'
    )

    @field_validator('frontend_dist_path', mode='before')
    @classmethod
    def blank_frontend_path_is_disabled(cls, value):
        return None if value == '' else value

    logging_level: Literal['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'] = Field(
        'INFO',
        description='Logging level for the application'
    )

    mongodb_host: str = Field(
        '127.0.0.1',
        description='Host for the local server.'
    )
    mongodb_port: int = Field(
        27017,
        description='Port for the local server.'
    )
    mongodb_name: str = Field(
        'roleplay-catalogue',
        description='Database name for the local server.'
    )
    mongodb_direct_connection: bool = Field(
        False,
        description='Whether to ignore the cluster discovery and connect to the target host directly'
    )
    mongodb_replica_set: str | None = Field(
        None,
        description='Replica set name. Transactions require a replica set or sharded cluster.'
    )

    @field_validator('mongodb_replica_set', mode='before')
    @classmethod
    def blank_replica_set_is_disabled(cls, value):
        return None if value == '' else value

    api_key_cleanup_interval: int = Field(
        21600,
        ge=60,
        description='Seconds between expired API key cleanup jobs.',
    )

    s3_endpoint_url: str | None = Field(
        None,
        description='Optional endpoint URL for S3-compatible object storage.'
    )
    s3_region: str = Field(
        'us-east-1',
        description='S3 region name.'
    )
    s3_access_key_id: str | None = Field(
        None,
        description='S3 access key ID.'
    )
    s3_secret_access_key: str | None = Field(
        None,
        description='S3 secret access key.'
    )
    s3_bucket: str = Field(
        'roleplay-catalogue',
        description='Bucket used for uploaded assets.'
    )
    s3_signed_url_expiry: int = Field(
        120,
        ge=1,
        le=604_800,
        description='Lifetime of direct S3 download links in seconds.',
    )
    image_max_bytes: int = Field(
        20 * 1024 * 1024,
        description='Maximum accepted source image size in bytes.'
    )
    world_bundle_max_bytes: int = Field(
        104_857_600,
        ge=1_048_576,
        description='Maximum compressed World bundle upload size.',
    )
    preset_max_bytes: int = Field(
        5 * 1024 * 1024,
        ge=1024,
        description='Maximum accepted SillyTavern preset JSON size.',
    )

    smtp_host: str = Field(
        '127.0.0.1',
        description='SMTP server hostname.'
    )
    smtp_port: int = Field(
        1025,
        description='SMTP server port.'
    )
    smtp_username: str | None = Field(
        None,
        description='Optional SMTP authentication username.'
    )
    smtp_password: str | None = Field(
        None,
        description='Optional SMTP authentication password.'
    )
    smtp_use_tls: bool = Field(
        False,
        description='Connect to SMTP using TLS from the start.'
    )
    smtp_start_tls: bool | None = Field(
        None,
        description='Whether to upgrade the SMTP connection using STARTTLS.'
    )
    smtp_sender: str = Field(
        'no-reply@localhost',
        description='From address used for outgoing email.'
    )
    public_base_url: str = Field(
        'http://127.0.0.1:5173',
        description='Public base URL used to build links in outgoing email.'
    )
    activation_token_max_age: int = Field(
        60 * 60 * 24,
        description='Activation token lifetime in seconds.'
    )
    pending_account_retention: int = Field(
        60 * 60 * 24,
        ge=3600,
        description='Seconds before an unactivated account is deleted.'
    )
    account_cleanup_interval: int = Field(
        60 * 60 * 6,
        ge=300,
        description='Seconds between pending-account cleanup runs.'
    )
    password_reset_token_max_age: int = Field(
        60 * 60,
        ge=300,
        description='Password reset token lifetime in seconds.'
    )
    session_secret: str = Field(
        default_factory=lambda: token_urlsafe(32),
        description='Secret used to sign session cookies. Set this explicitly in production.'
    )
    session_cookie_name: str = Field(
        'roleplay_catalogue_session',
        description='Name of the session cookie.'
    )
    session_max_age: int = Field(
        60 * 60 * 24 * 14,
        description='Maximum session lifetime in seconds.'
    )
    session_cookie_secure: bool = Field(
        False,
        description='Only send the session cookie over HTTPS.'
    )
    security_headers_enabled: bool = Field(
        True,
        description='Add baseline browser security headers to HTTP responses.'
    )
    content_security_policy: str = Field(
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'none'; form-action 'self'",
        description='Content-Security-Policy value. Override for external frontend dependencies.'
    )
    hsts_max_age: int = Field(
        0,
        ge=0,
        description='Strict-Transport-Security max-age. Zero disables HSTS.'
    )
    hsts_include_subdomains: bool = Field(False)
    hsts_preload: bool = Field(False)


CONFIG = Settings(_env_file=os.getenv('RC_ENV_FILE', '.env'))      # type: ignore
