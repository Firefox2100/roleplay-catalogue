# World Simulation Engine Bundles

## Overview

Worlds in the Roleplay Catalogue are complete packages designed for the **World Simulation Engine (WorldSE)**. They are uploaded as ZIP bundles containing game data — including scenes, characters, maps, scripts, and world configuration — plus embedded images.

Worlds function as standalone settings, modules, or expansions that characters can interact with in a conversation. Each world is a first-class catalogue resource: it has a name, description, tags, visibility setting, language, version history, and an exported ZIP artifact.

## How to Use

### Uploading a World Bundle

1. Open the world editor in the Catalogue.
2. Click **Upload** and select your `.zip` WorldSE bundle file.
3. The Catalogue validates the bundle structure and processes it:
   - Embedded images are extracted and stored as **independent image resources**.
   - The language is detected automatically from the world's internal data.
   - Tags from the bundle metadata are merged with any additional tags you provide.
4. Provide a **name** (required, up to 200 characters) and an optional **description** (up to 10,000 characters).
5. Set visibility, add tags, and choose a language if not auto-detected.
6. Submit to upload.

### Setting a Cover Image

1. In the world editor, open the **cover image** section.
2. Use the **"Select cover image"** flow to browse images that were extracted from your world bundle (or any other uploaded images).
3. Save the world — the cover now points to the selected image.

Images embedded in the uploaded ZIP that qualify as cover-worthy are automatically added to your image library.

### Importing Tag Data

Tags from the world's game-data metadata are **merged** with any tags you add via the Catalogue resource editor. This preserves both the world's built-in categorisation and your custom catalogue tags. You can view the combined tag list on the published world page.

### Exporting a World

1. Open the published world detail page.
2. Click the **Export** button.
3. Download a `.zip` file containing the full world bundle with all embedded images — the same format you uploaded.

This ZIP is ready to use offline with the WorldSE client.

### World Data Schema

A published world includes the following data:

- **World configuration** — engine settings, default parameters, and global options.
- **Scenes** — defined locations or stages that characters can move through.
- **Characters** — NPCs and entities defined within the world.
- **Maps** — spatial layouts and positional reference data.
- **Scripts** — custom logic files executed by the WorldSE engine.

### Artifact Verification

Every published world records an `artifact_file_name` and `artifact_sha256` hash. Use these to verify the integrity of a downloaded ZIP file against the published version.

### Forking a World

1. Open any published world.
2. Choose **Fork**.
3. The Catalogue creates a new world resource. The zip artifact is built from the source's data, with the fork author credited as the uploader.
4. Referenced images are either:
   - **Reused** if a copy already exists for the fork author (deduplicated by SHA-256 hash).
   - **Copied** into the fork author's storage if no matching copy exists.
5. Edit and republish the forked world independently.

## Constraints

| Constraint | Limit |
| --- | --- |
| Maximum bundle size (`world_bundle_max_bytes`) | 100 MiB (104,857,600 bytes) |
| Accepted format | ZIP bundle with WorldSE data |
| Export format | ZIP |
| Content diff | `null` (binary ZIP format has no textual representation) |
| Supported languages | Detected from world data (English and Chinese Simplified) |
| Artifacts verified by | `artifact_sha256` |
| Resource type filter | Searchable via `resourceType=world` |

## Tips and Notes

- **Self-contained exports.** Downloaded ZIP bundles include all embedded images. You do not need an active Catalogue connection to use a world offline.
- **Images carry their own identity.** Extracted images are full catalogue resources — you can change their name, description, or tags independently of the world they came from.
- **Merge-friendly tags.** Because world data tags and catalogue tags are merged, you can add additional descriptive tags in the Catalogue without losing the tags the world bundle originally shipped with.
- **Dedup on fork.** When forking a world that references an image already stored in the Catalogue, your fork reuses that image. Only images not yet catalogued are copied, saving storage and keeping downloads fast.
- **Hash verification.** Always verify the `artifact_sha256` of a downloaded world bundle against the published hash to ensure the file was not corrupted during transfer.
- **Binary format.** World bundles use a binary ZIP format, so `content_diff` is `null` for all published world versions.
