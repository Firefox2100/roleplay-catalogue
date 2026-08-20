# Configuration

The Roleplay Catalogue is configured entirely through environment variables. Every variable is prefixed with `RC_` unless it belongs to an external service (MongoDB, MinIO, etc.). The canonical reference is `example.env` at the repository root — copy it to `.env` before first use.

All configuration is validated at startup by a [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) model. Invalid values cause the container to exit with an error message.

## Docker Compose variables

These variables come from `compose.yaml` and affect the Docker environment. They either override `.env` or read values from it.

| Variable | Default | Description |
|---|---|---|
| `CATALOGUE_PORT` | `8080` | Host port exposed for the catalogue web interface. |
| `NGINX_HSTS_HEADER` | empty | Complete HSTS header value injected into the Nginx response (e.g. `max-age=31536000; includeSubDomains`). Only effective in Docker mode. |
| `NGINX_CONTENT_SECURITY_POLICY` | see `example.env` | CSP header override for the Nginx response. Only effective in Docker mode. |

## Application server

| Variable | Default | Description |
|---|---|---|
| `RC_APP_HOST` | `127.0.0.1` | Host the Uvicorn worker binds to. |
| `RC_APP_PORT` | `9798` | Port the Uvicorn worker listens on. |
| `RC_LOGGING_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |

## API prefix

| Variable | Default | Description |
|---|---|---|
| `RC_API_PREFIX` | empty | Prefix added to all FastAPI routes. Set to `/api` when the frontend mounts the SPA at `/` and routes `/api/*` requests to the backend. Leave empty for a bare deployment. |
| `RC_FRONTEND_DIST_PATH` | empty | Absolute path to a built Vite `dist/` directory. When set, FastAPI serves the SPA from `/` with client-side routing fallback. Leave empty when an external reverse proxy or CDN serves the frontend. |

## MongoDB

| Variable | Default | Description |
|---|---|---|
| `RC_MONGODB_HOST` | `127.0.0.1` | MongoDB hostname (or comma-separated list for a replica set). |
| `RC_MONGODB_PORT` | `27017` | MongoDB port. |
| `RC_MONGODB_NAME` | `roleplay-catalogue` | Database name. |
| `RC_MONGODB_DIRECT_CONNECTION` | `false` | If `true`, bypasses the replica set discovery mechanism and connects directly to the host listed in `RC_MONGODB_HOST` only. Replica set mode is required for transactions. |
| `RC_MONGODB_REPLICA_SET` | `rs0` | Replica set name. The `mongod` command-line `--replSet` flag must match this value. Leave blank for a standalone MongoDB connection. |
| `RC_MONGODB_USERNAME` | empty | Optional username for MongoDB authentication. Leave both this and `RC_MONGODB_PASSWORD` empty to connect without authentication. |
| `RC_MONGODB_PASSWORD` | empty | Optional password for MongoDB authentication, paired with `RC_MONGODB_USERNAME`. Authenticated against the `RC_MONGODB_NAME` database (`authSource`). |

MongoDB transactions are required for atomic multi-document operations (e.g. creating a resource, its draft data, and indexed searches in a single atomic write). A single-node replica set is sufficient for local development as provisioned by `compose.yaml`.

## Redis

| Variable | Default | Description |
|---|---|---|
| `RC_REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection URL. Redis is the authoritative store for expiring activation and password-reset credentials. |
| `RC_CACHE_KEY_PREFIX` | `roleplay-catalogue` | Prefix applied to all keys owned by this application. Use a distinct value when sharing a Redis database. |

## S3-compatible storage

The application uses S3-compatible storage for resource artifacts (character card files, lorebook files, preset files, images, and World Simulation Engine bundles). Any S3 API implementation works (AWS S3, MinIO, Cloudflare R2, etc.).

| Variable | Default | Description |
|---|---|---|
| `RC_S3_ENDPOINT_URL` | `http://127.0.0.1:9000` | S3 API endpoint URL. Set to `https://s3.amazonaws.com` or your provider's endpoint for production. |
| `RC_S3_REGION` | `us-east-1` | AWS region identifier. Some providers require an empty string instead. |
| `RC_S3_ACCESS_KEY_ID` | `minioadmin` | S3 access key. |
| `RC_S3_SECRET_ACCESS_KEY` | `minioadmin` | S3 secret key. |
| `RC_S3_BUCKET` | `roleplay-catalogue` | S3 bucket name. The bucket is created automatically by the Docker Compose initialisation job; for external services ensure it already exists. |
| `RC_IMAGE_MAX_BYTES` | `20971520` (20 MiB) | Maximum allowed size for image uploads (cover images, standalone images). |
| `RC_WORLD_BUNDLE_MAX_BYTES` | `104857600` (100 MiB) | Maximum allowed size for World Simulation Engine bundle uploads. |
| `RC_PRESET_MAX_BYTES` | `5242880` (5 MiB) | Maximum allowed size for SillyTavern preset uploads. |

## SMTP (email)

| Variable | Default | Description |
|---|---|---|
| `RC_SMTP_HOST` | `127.0.0.1` | SMTP server hostname. Leave empty to disable email features (account activation tokens, password reset tokens). |
| `RC_SMTP_PORT` | `1025` | SMTP server port. |
| `RC_SMTP_USERNAME` | empty | SMTP username for authentication. |
| `RC_SMTP_PASSWORD` | empty | SMTP password for authentication. |
| `RC_SMTP_USE_TLS` | `false` | Enable TLS on connect (SMTPS / implicit TLS on port 465). |
| `RC_SMTP_START_TLS` | `false` | Start with plaintext and upgrade to TLS with `STARTTLS` (port 587). |
| `RC_SMTP_SENDER` | `no-reply@localhost` | Email address used as the `From` header in all outgoing mail. |

Account activation tokens and password-reset tokens are delivered by email. Unactivated accounts are purged after `RC_PENDING_ACCOUNT_RETENTION` seconds (default 24 hours).

## Email and public URLs

| Variable | Default | Description |
|---|---|---|
| `RC_PUBLIC_BASE_URL` | `http://127.0.0.1:5173` | The external-facing URL of the frontend application. Used to construct activation and password-reset links in emails. Must exactly match the address users navigate to, including scheme. |

## Session and authentication

| Variable | Default | Description |
|---|---|---|
| `RC_SESSION_SECRET` | *(required)* | Secret key used to sign session cookies. Minimum 32 bytes recommended. |
| `RC_SESSION_COOKIE_NAME` | `roleplay_catalogue_session` | Name of the session cookie. |
| `RC_SESSION_MAX_AGE` | `1209600` (14 days) | Maximum age of a session in seconds, applied on each request. |
| `RC_SESSION_COOKIE_SECURE` | `false` | Set the `Secure` flag on the session cookie so it is only sent over HTTPS. Set to `true` for production deployments. |
| `RC_ACTIVATION_TOKEN_MAX_AGE` | `86400` (24 hours) | Maximum age of a user-activation token (seconds). |
| `RC_PENDING_ACCOUNT_RETENTION` | `86400` (24 hours) | How long to keep unactivated user accounts before soft deletion (seconds). |
| `RC_ACCOUNT_CLEANUP_INTERVAL` | `21600` (6 hours) | How often the background job scans for expired pending accounts (seconds). |
| `RC_PASSWORD_RESET_TOKEN_MAX_AGE` | `3600` (1 hour) | Maximum age of a password-reset token (seconds). |
| `RC_API_KEY_CLEANUP_INTERVAL` | `21600` (6 hours) | How often the background job purges expired API keys (seconds). |

The application supports two authentication modes: session cookies (browser logins) and bearer API keys (programmatic access). Both are validated by the same dependency layer in the routers.

## Browser security headers

| Variable | Default | Description |
|---|---|---|
| `RC_SECURITY_HEADERS_ENABLED` | `true` | Whether to inject security headers at the FastAPI middleware level. Set to `false` when an upstream proxy (Nginx, Cloudflare, etc.) manages them. |
| `RC_CONTENT_SECURITY_POLICY` | see `example.env` | CSP header value. A strict "default-src 'self'" policy with image data/blob sources is included by default. Override when the frontend loads external assets or APIs. |
| `RC_HSTS_MAX_AGE` | `0` | HSTS `max-age` in seconds. Zero disables HSTS. Set to `31536000` for one year in HTTPS-only production. |
| `RC_HSTS_INCLUDE_SUBDOMAINS` | `false` | Add the `includeSubDomains` directive to the HSTS header. |
| `RC_HSTS_PRELOAD` | `false` | Add the `preload` directive to the HSTS header. |

> [!NOTE]
> In Docker Compose mode, the Nginx sidecar serves the frontend directly. HSTS configuration for `NGINX_HSTS_HEADER` and `NGINX_CONTENT_SECURITY_POLICY` applies to those Nginx responses. Set both the FastAPI env var (for API responses) and the Nginx variable (for the SPA) for a consistent policy.

## CSFR protection

Cross-Site Request Forgery protection is provided by a middleware that requires the `x-csrf-token` header on every unsafe request (GET and OPTIONS requests are exempt). The token itself comes from a previous `SEC_COOKIE_NAME` cookie. API-key authenticated requests are exempt from CSRF checks.
