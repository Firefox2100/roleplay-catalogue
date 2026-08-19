# Roleplay Catalogue

A FastAPI and React catalogue for versioned roleplay characters, lorebooks, and images.

## Development

The frontend development server sends `/api` requests to FastAPI and strips that prefix. Start
FastAPI on port 9798 and Vite from `frontend/` on port 5173. Copy `example.env` to `.env` and set
MongoDB, S3-compatible storage, SMTP, and session values first.

## Frontend deployment

The frontend can be hosted by a reverse proxy/CDN or served by FastAPI:

- Proxy/CDN: leave `RC_FRONTEND_DIST_PATH` and `RC_API_PREFIX` blank, and route external `/api/*`
  requests to the corresponding unprefixed FastAPI path.
- Single service: build `frontend/`, set `RC_FRONTEND_DIST_PATH` to its absolute `dist` directory,
  and set `RC_API_PREFIX=/api`. FastAPI then serves the SPA, including client-side route fallback.

`RC_PUBLIC_BASE_URL` is the browser-facing frontend URL used in activation emails. This makes the
external frontend address independent of the internal Docker or local service address.

## Browser security headers

Baseline security headers and a same-origin CSP are enabled by default. Override
`RC_CONTENT_SECURITY_POLICY` when the frontend intentionally uses external asset or API origins, or
disable all added headers with `RC_SECURITY_HEADERS_ENABLED=false` when an upstream proxy owns them.

HSTS is disabled by default. Enable it only for an HTTPS-only deployment using
`RC_HSTS_MAX_AGE`; `RC_HSTS_INCLUDE_SUBDOMAINS` and `RC_HSTS_PRELOAD` are separate opt-ins. Local HTTP
and mixed deployment environments should keep the max age at zero.
For the all-in-one container, set `NGINX_HSTS_HEADER` to the complete HSTS value because Nginx
serves frontend responses directly. `NGINX_CONTENT_SECURITY_POLICY` similarly overrides its CSP.

## Account lifecycle API

Unactivated accounts are removed after `RC_PENDING_ACCOUNT_RETENTION` seconds. An APScheduler job
runs every `RC_ACCOUNT_CLEANUP_INTERVAL` seconds; the defaults are 24 hours and 6 hours respectively.
The account creation timestamp is authoritative, so MongoDB's activation-token TTL cleanup cannot
cause an expired account to be missed.

The backend exposes the following API-only account workflows. All state-changing requests require
the normal CSRF header:

- `POST /auth/password-reset/request` with `{ "email": "..." }` always returns 202.
- `POST /auth/password-reset/confirm` accepts `userId`, `token`, and `newPassword`.
- `POST /auth/password` accepts authenticated `currentPassword` and `newPassword`.
- `DELETE /auth/account` accepts the current `password` and permanently deletes the account.

Account deletion cascades through authored resources, release snapshots, draft data, image objects,
and generated release artifacts. Email address changes are intentionally unsupported.

## Resource co-authors

A resource's author may grant other users editing permission on its draft:

- `POST /resources/{resourceId}/co-authors` with `{ "username": "..." }`, author only.
- `DELETE /resources/{resourceId}/co-authors/{coAuthorId}`, author or the co-author themselves.

Co-authors can view and edit the draft exactly like the author, including uploading data, editing
metadata, and linking it as a draft dependency from another resource they can edit. They cannot
publish a release or delete the resource; those actions remain author-only. Deleting a user account
removes it from every other resource's co-author list.

## Container deployment

The multistage [Dockerfile](Dockerfile) builds the Vite frontend, builds the Python project and all
dependency wheels in an isolated stage, and installs only wheels into the runtime image. Supervisor
runs Uvicorn and Nginx; Nginx serves the SPA on port 8080 and reverse-proxies `/api/` to Uvicorn.

The provided [compose.yaml](compose.yaml) pulls the catalogue image and starts MongoDB Community
Server as a single-node replica set, MongoDB Community Search (`mongot`), and MinIO with persistent
volumes. The replica set enables database transactions; the separate Search process leaves the
deployment ready for future `$search` and vector-search indexes. It also creates the configured S3
bucket. Set at least `RC_SESSION_SECRET`, `MONGOT_PASSWORD`, `RC_PUBLIC_BASE_URL`, SMTP settings,
and non-default S3 credentials before deployment, then run:

```sh
docker compose up -d
```
