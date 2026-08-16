import os
from secrets import token_urlsafe
from typing import Literal
from pydantic import Field
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


CONFIG = Settings(_env_file=os.getenv('RC_ENV_FILE', '.env'))      # type: ignore
