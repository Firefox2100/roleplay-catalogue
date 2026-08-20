# Deployment

The Roleplay Catalogue ships a ready-made Docker image and can also be deployed from source. There are two deployment models:

| Model | What it does |
|---|---|
| **All-in-one** (Docker Compose) | Runs the application and all required data services from the supplied Compose file. |
| **Split** | Standalone FastAPI backend at `/api` + any SPA host (reverse proxy, CDN, S3 bucket). You build the frontend yourself and choose where to run Uvicorn. |

---

## Prerequisites

- **Python** ≥ 3.12
- **Node.js** ≥ 18 (for building the frontend)
- **MongoDB** running as a **replica set** (single-node replica set is fine for local / small deployments) — mandatory because the app uses multi-document transactions.
- **Redis** with persistence enabled — stores activation and password-reset credentials plus resource view and download counters.
- **S3-compatible storage** (MinIO, AWS S3, Cloudflare R2, etc.) — required for uploading character cards, lorebooks, presets, images, and world bundles.

---

## Option 1 — Docker Compose (recommended)

The provided `compose.yaml` starts five long-running services:

| Service | Purpose | Docker image |
|---|---|---|
| `catalogue` | Nginx (port 8080) proxies `/api/` to Uvicorn on port 9798 and serves the SPA. | `ghcr.io/Firefox2100/roleplay-catalogue:latest` |
| `redis` | Persistent activation/reset credentials and resource counters. | `redis:8-alpine` |
| `mongodb` | MongoDB Community Server, single-node replica set `rs0`, authentication enabled. | `mongodb/mongodb-community-server:latest` |
| `mongodb-search` (mongot) | MongoDB Community Search for full-text and vector indexes. | `mongodb/mongodb-community-search:latest` |
| `minio` | S3-compatible object storage on port 9000 (console on 9001). | `minio/minio:latest` |

Two one-shot initialisation containers (`mongodb-init`, `minio-init`) run once after MongoDB and MinIO become healthy:
- `mongodb-init` executes `init-mongodb.sh` (configures the replica set, enables authentication,
  and provisions the mongot search user plus the application's own database user).
- `minio-init` creates the S3 bucket configured in `RC_S3_BUCKET`.

MongoDB runs with `security.authorization: enabled` and a generated keyfile (for internal
replica-set authentication). `mongodb-init` bootstraps a cluster-admin user
(`MONGODB_ROOT_USERNAME` / `MONGODB_ROOT_PASSWORD`, used only during provisioning) and then
creates the application's own scoped user (`RC_MONGODB_USERNAME` / `RC_MONGODB_PASSWORD`, with
`readWrite` on `RC_MONGODB_NAME` only) that the `catalogue` service actually connects with.

### Steps

```sh
# 1. Copy and edit the environment file
cp example.env .env
# Edit at least RC_SESSION_SECRET, MONGOT_PASSWORD, RC_PUBLIC_BASE_URL.
# Also change MONGODB_ROOT_PASSWORD, RC_MONGODB_USERNAME and RC_MONGODB_PASSWORD
# from their insecure defaults before exposing this beyond your own machine.

# 2. Start
docker compose up -d

# 3. Verify
docker compose ps           # all containers should show Up
docker compose logs -f catalogue   # tail app logs
```

### Nginx inside the container

The `catalogue` image embeds an Nginx configuration (templated on build at
`deploy/nginx.conf`). It performs:

- `location /api/` → proxy to Uvicorn on `127.0.0.1:9798` with
  `proxy_read_timeout 300s` and no client-body buffering.
- `location /` → SPA fallback to `index.html` for client-side routing.
- `client_max_body_size 21m` — raises above the default 1 m so large image
  uploads succeed. Adjust with your own image or by editing the rendered
  Nginx config.

The container exposes **port 8080** (mapped from `CATALOGUE_PORT`). All browsers
connect there; `/api/*` requests go transparently to the backend through Nginx.

### Customising the compose stack

You can override any compose.yaml value via `.env` or environment variables on
the `catalogue` service. The `CATALOGUE_PORT` variable controls the host port
mapped to the container; `RC_SESSION_SECRET`, `MONGOT_PASSWORD`,
`MONGODB_ROOT_USERNAME`, `MONGODB_ROOT_PASSWORD`, `RC_MONGODB_USERNAME`,
`RC_MONGODB_PASSWORD`, `RC_PUBLIC_BASE_URL`, SMTP settings, and S3 credentials
are populated from `.env` before the first start.

`RC_MONGODB_USERNAME`/`RC_MONGODB_PASSWORD` can be left blank to run MongoDB
without authentication — useful when pointing `RC_MONGODB_HOST` at an
externally managed, already-secured MongoDB instead of the bundled one. The
bundled `mongodb` service in `compose.yaml` always enables authentication,
though, so leaving them blank there means the `catalogue` container will fail
to authenticate; only leave them blank if you also disable
`security.authorization` in `deploy/mongod.conf` and skip user provisioning.

---

## Option 2 — Split deployment from source

Choose this when you want to decouple the SPA frontend from the Python backend
(e.g. you already have a CDN, or you deploy backend and frontend on different
machines).

### 2.1 Build the frontend

```sh
cd frontend
npm ci
npm run build          # produces frontend/dist/
```

Copy `frontend/dist/` to your preferred hosting target:

| Hosting | How-to |
|---|---|
| **Nginx (standalone)** | `sudo cp -r dist/* /var/www/roleplay-catalogue/` and serve via Nginx on `/`. Enable SPA fallback (`try_files $uri $uri/ /index.html`). |
| **Cloudflare Pages / Vercel / any CDN** | Deploy the `dist/` directory as a static site. Ensure `index.html` is the single-page fallback. |
| **S3 + CloudFront** | Upload `dist/` contents to an S3 bucket configured as a static site, point CloudFront at it, and enable SPA fallback to `index.html`. |

### 2.2 Run the backend

```sh
# Create and activate a virtualenv (Python 3.12)
python3 -m venv .venv
source .venv/bin/activate
pip install .

# Copy and edit the environment file
cp example.env .env
# Set RC_FRONTEND_DIST_PATH=""   (not needed in split mode)
# Set RC_API_PREFIX=/api         # or leave blank when using a separate proxy
```

Start Uvicorn directly or via your preferred process manager:

```sh
# Direct (development)
# Uvicorn binds to RC_APP_HOST:RC_APP_PORT (default 127.0.0.1:9798)
uvicorn roleplay_catalogue.main:app --host 0.0.0.0 --port 9798

# Production — run via systemd, supervisord, docker, k8s, etc.
```

Or run inside a lightweight container:

```sh
docker run --rm -p 9798:9798 \
  -e RC_MONGODB_HOST=mongodb \
  -e RC_S3_ENDPOINT_URL=http://minio:9000 \
  -e RC_API_PREFIX=/api \
  ghcr.io/fk2100/fastapi-uvicorn:latest \
  bash -c "pip install roleplay-catalogue && uvicorn roleplay_catalogue.main:app --host 0.0.0.0 --port 9798"
```

### 2.3 Frontend ↔ backend connection

The frontend and backend communicate over the **API prefix** path:

- `RC_API_PREFIX` is set to `/api` on the backend.
- The frontend's base URL must include that prefix: the browser requests to
  `https://example.com/api/resources` hit the SPA (served by the CDN/Nginx),
  which sends an XHR/fetch request to `/api/resources`.
- Your **reverse proxy** must forward `https://your-domain/api/*` to the backend
  (running on its own host and port). Example Apache:

  ```apache
  ProxyPass /api http://backend-host:9798/
  ProxyPassReverse /api http://backend-host:9798/
  ```

- Or Nginx:

  ```nginx
  location /api/ {
      proxy_pass http://backend-host:9798/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  ```

> [!IMPORTANT]
> Backend must serve at the `/api` path relative to the public URL. If the backend
> is at `https://backend.example.com` and you want its API under
> `https://example.com/api`, an intermediary reverse proxy or load balancer must
> rewrite the path. Uvicorn strips one path component by default with
> `proxy_pass` to `http://backend/` (not `http://backend/api/`).

### 2.4 Required env variables (split mode)

The following are **essential**; everything else falls back to `example.env` defaults.

| Variable | Example value | Notes |
|---|---|---|
| `RC_SESSION_SECRET` | `a3f1b7c9d2e4...` | Minimum 32 bytes |
| `RC_MONGODB_HOST` | `10.0.1.5` | Host or replica-set seed |
| `RC_MONGODB_REPLICA_SET` | `rs0` | Must match `mongod --replSet` |
| `RC_MONGODB_USERNAME` | `roleplay_catalogue` | Optional; leave both this and `RC_MONGODB_PASSWORD` unset to connect without auth |
| `RC_MONGODB_PASSWORD` | `abc123...` | Optional, paired with `RC_MONGODB_USERNAME` |
| `RC_REDIS_URL` | `redis://redis-host:6379/0` | Persistent Redis database; do not treat it as disposable cache storage |
| `RC_S3_ENDPOINT_URL` | `https://my-bucket.r2.cloudflarestorage.com` | No trailing slash |
| `RC_S3_REGION` | `auto` | Some providers require this literal value |
| `RC_S3_ACCESS_KEY_ID` | `AKIA...` | |
| `RC_S3_SECRET_ACCESS_KEY` | `abc123...` | |
| `RC_PUBLIC_BASE_URL` | `https://roleplay.example.com` | Browser-facing URL; used in email links |
| `RC_API_PREFIX` | `/api` | Must match the path under the public URL |
| `RC_SMTP_HOST` | `smtp.gmail.com` | Set to empty string to disable emails |
| `RC_SMTP_PORT` | `587` | Together with `RC_SMTP_START_TLS=true` |
| `RC_SMTP_USERNAME` | `you@example.com` | |
| `RC_SMTP_PASSWORD` | `app-key` | |

---

## Reverse-proxy notes

When running behind an HTTPS reverse proxy (Traefik, Caddy, HAProxy, Cloudflare,
etc.), the proxy must **strip one leading slash** from `/api/*` before forwarding
to Uvicorn, because the backend is mounted under `RC_API_PREFIX=/api`. Some
proxies forward `/api/resources` → `http://backend:9798/api/resources` (double
`/api`); ensure the `ProxyPass` or `location` block maps to `http://backend:9798/`
(not `/api/`).

---

## Deployment checklist

- [ ] `RC_SESSION_SECRET` set to ≥ 32 random characters.
- [ ] MongoDB is a **replica set** (`--replSet` flag matches `RC_MONGODB_REPLICA_SET`).
- [ ] Redis persistence and backups meet your retention requirements; losing Redis also loses counters and outstanding activation/reset credentials.
- [ ] `MONGODB_ROOT_PASSWORD`, `RC_MONGODB_USERNAME`, and `RC_MONGODB_PASSWORD` changed from
  their insecure `compose.yaml` defaults (Docker Compose deployments only).
- [ ] S3 bucket exists and credentials are correct (in split mode).
- [ ] `RC_PUBLIC_BASE_URL` matches the exact public domain + scheme users navigate to.
- [ ] Reverse proxy forwards `/api/*` → `http://backend-host/api/` (one-level strip).
- [ ] `RC_SMTP_HOST` is set (or left empty to disable email if activation is optional).
- [ ] Security headers: `RC_HSTS_MAX_AGE > 0` and HTTPS-only before enabling.
- [ ] `RC_CONTENT_SECURITY_POLICY` checked for compatibility with any external
  assets or 3rd-party integrations (e.g. a SillyTavern instance loading cards).
