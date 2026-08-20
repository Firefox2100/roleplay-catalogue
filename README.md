# Roleplay Catalogue

[![License: GPL v3](https://www.gnu.org/graphics/gplv3-88x31.png)](https://www.gnu.org/licenses/gpl-3.0.en.html) [![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=Firefox2100_roleplay-catalogue&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Firefox2100_roleplay-catalogue) [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Firefox2100_roleplay-catalogue&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Firefox2100_roleplay-catalogue) [![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Firefox2100_roleplay-catalogue&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Firefox2100_roleplay-catalogue)

An open-source, self-hosted library for managing and sharing SillyTavern character cards, lore books, chat presets, images, and World Simulation Engine worlds.

## Purpose

The Roleplay Catalogue fills the gap for private or group-maintained content libraries. It offers features for three groups:

- **Users** — discover, search, and download resources.
- **Authors** — create, version, and publish resources with collaborative editing support.
- **Administrators** — operate the complete service with Docker Compose or connect managed infrastructure.

A deployed instance holds no content filtering or included content; the hoster controls what is published. The catalogued resources are shared under each author's own license (GPL-3.0 by default applies to the platform itself, not the content hosted within it).

## Features

- **SillyTavern character cards** — Upload and download in V3 format (V2 cards auto-convert on upload).
- **Lore books** — First-class resource type with linking from character cards, reusable across multiple resources.
- **Chat presets** — Create, share, and download SillyTavern generation presets.
- **World Simulation Engine** — Upload and serve WorldSE world bundles.
- **Images** — Upload, manage, and assign cover images to any resource.
- **Versioned releases** — Every resource supports draft → publish with numbered version history and unified content diffs (including merged linked lorebooks).
- **Forking** — Users can fork any public resource to create a derived version while linking back to the original.
- **Collaborative editing** — Authors invite co-authors to edit a resource's draft (publish and delete remain author-only).
- **Search and filtering** — Discover resources by text, tags, type, and author; powered by MongoDB Community Search.
- **Engagement counts** — See anonymous view and download counts on listings and detail pages.
- **Two auth modes** — Session cookies for browser logins and Bearer API keys for programmatic access.
- **CSRF protection** — Middleware-enforced token header on unsafe requests; API-key auth is exempt.
- **I18n** — English and Chinese Simplified built in via `react-i18next`.

## Quick Start

The fastest way to run everything locally is Docker Compose. It provisions the application server,
a MongoDB replica set (required for transactions), Redis for expiring credentials and resource counters, a MinIO S3
storage backend, and MongoDB Community Search.

### 1. Clone and configure

```sh
git clone https://github.com/Firefox2100/roleplay-catalogue.git
cd roleplay-catalogue
cp example.env .env
```

Edit `.env` and set at minimum:

```sh
# Your own secret (32+ characters)
RC_SESSION_SECRET=change-me-to-something-secret

# MongoDB Community Search password
MONGOT_PASSWORD=change-me-too-S3cr3t-Pass

# The URL users navigate to
RC_PUBLIC_BASE_URL=http://localhost:8080
```

For a full list of configurable options, see [Configuration](docs/en/configuration.md).

### 2. Start the stack

```sh
docker compose up -d
```

Wait a minute for MongoDB initialisation and bucket creation. Then open `http://localhost:8080` in your browser.

### 3. Register

Visit the home page, click **Register**, fill in your email and password, check your inbox for the activation link, and you're in. Create your first resource from the home page or your profile.

### 4. Stop and restart

```sh
docker compose down          # stop containers (volumes stay)
docker compose down -v       # stop and remove everything
docker compose restart       # restart all services
docker compose logs -f       # follow logs
```

## License

The Roleplay Catalogue is free software under the [GPL v3 license](https://www.gnu.org/licenses/gpl-3.0.en.html). All derivative works must also use GPL v3. The software comes with no warranty. By using it you agree to these terms and to the [disclaimer](docs/en/index.md).

## Links

- **GitHub:** [Firefox2100/roleplay-catalogue](https://github.com/Firefox2100/roleplay-catalogue)
- **Documentation:** [https://firefox2100.github.io/roleplay-catalogue/](https://firefox2100.github.io/roleplay-catalogue/)
