# Quick Start

The fastest way to run the Roleplay Catalogue locally is with `docker compose`. This starts the application server, a single-node MongoDB replica set, MongoDB Community Search (for future full-text and vector search), and a MinIO S3-compatible storage backend — everything you need in one command.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) v2.20+

## Steps

1. **Copy the example environment file**

   ```sh
   cp example.env .env
   ```

2. **Edit `.env` and set at least the following**

   | Variable | Example | Notes |
   |---|---|---|
   | `RC_SESSION_SECRET` | `a3f1b7c9d2e4f6...` | Minimum 32 bytes recommended |
   | `MONGOT_PASSWORD` | `my-redis-12345` | Random password for MongoDB Community Search |
   | `RC_PUBLIC_BASE_URL` | `http://localhost:8080` | The URL users will type in their browser |

   See [Configuration](configuration.md) for the full list of options. All other values use sensible defaults.

3. **Start the stack**

   ```sh
   docker compose up -d
   ```

   On first run Docker will pull the images, start the container, and run two one-shot initialisation jobs: it creates the S3 bucket and configures MongoDB as a replica set. This may take a minute or two.

4. **Open the catalogue**

   Navigate to `http://localhost:8080` (or whatever port you configured via `CATALOGUE_PORT`). The first time you visit the home page you'll see a "Register" button — create an account to log in.

## Stopping and restarting

```sh
docker compose down          # stop and remove containers (volumes kept)
docker compose down -v       # stop and remove everything including volumes
docker compose restart       # restart all running services
```

## Viewing logs

```sh
docker compose logs -f catalogue   # only the application server
docker compose logs -f             # all services
```

## Single command (defaults only)

If you don't want to edit `.env` at all, these four defaults are enough to get a running instance:

```sh
cat > .env <<EOF
RC_SESSION_SECRET=change-me-to-something-secret
MONGOT_PASSWORD=change-me-too-S3cr3t-Pass
RC_PUBLIC_BASE_URL=http://localhost:8080
EOF

docker compose up -d
```

> [!TIP]
> The MongoDB replica set is required for database transactions. A single-node replica set is sufficient for development; production deployments should use a multi-node replica set for high availability.

> [!NOTE]
> Ports: the catalogue listens on `8080` inside the container, mapped to `CATALOGUE_PORT` (default `8080`). MinIO Console is available on port `9001` when running the compose stack.
