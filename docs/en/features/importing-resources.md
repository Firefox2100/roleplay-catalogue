# Importing Resources

The **import** feature lets you merge external content into an existing resource's draft. Import is a **post-creation** operation — you must first create a resource with a name and basic metadata, then import data into it.

## Overview

Import handles three scenarios:

- **Merge**: The resource already has draft data. The imported content fills blank fields or appends to existing lists, preserving what's already there.
- **Initialisation**: The resource has no draft data yet. Import creates the initial draft from the imported content.

### The merge strategy

When importing into an existing draft, the system uses a **recursive merge** algorithm:

| Data type | Merge behaviour |
|---|---|
| Strings | Existing value is kept; imported value fills only when current is empty |
| Lists | Concatenated; duplicates are removed |
| Dictionaries | Merged recursively — existing keys are preserved; new keys are added |
| Nested objects | Recursively merged at each level |

Import never overwrites existing non-blank content. This means your existing edits are safe when importing a new card, lorebook, or preset.

## How to import by type

### Character cards

**Endpoint**: `POST /resources/{resourceId}/import-card`
**Formats**: `.json` (V2 or V3) or `.png` (character card image)

The card import endpoint:

1. Accepts a SillyTavern character card in **V2 or V3** JSON format. V2 cards are automatically converted to V3 format during import.
2. Accepts a **PNG image** containing an embedded character card (the system reads `tEXt` chunks — `ccv3` for V3, `chara` for V2).
3. Imports the character data into the draft.

When importing into an existing character card:

- **Tags**: Imported tags are appended to existing tags if not already present (deduplication).
- **Description**: The existing description is preserved; the imported description fills only when the current description is empty.
- **Cover image**: If you import a PNG, the PNG file becomes the resource's cover image (stored as an independent image resource).
- **Lorebook**: If the PNG/V3 JSON contains an embedded lorebook, it is extracted and merged into the resource draft.

> [!TIP]
> **Import into an existing card to keep your edits.** If you've customised a character card and receive an updated version from the author, import the new card to pick up changes while keeping your modifications.

### Lorebooks

**Endpoint**: `POST /resources/{resourceId}/import-lorebook`
**Formats**: `.json` (V3 lorebook or card with embedded book) or `.png` (card PNG with embedded lorebook)

The lorebook import endpoint:

1. Accepts a standalone lorebook in **V3** JSON format (`lorebook_v3` spec).
2. Accepts a **character card JSON** (`chara_card_v2` or `chara_card_v3` spec) that contains an embedded lorebook in its `character_book` field.
3. Accepts a **PNG** containing either a V3 lorebook or a character card with embedded lore.

When importing into an existing lorebook draft:

- Lorebook entries are merged by their `entryOrder` / `key` identifiers.
- New entries are appended; existing entries are preserved.
- Definitions within each entry are recursively merged.

### Presets

**Endpoint**: `POST /resources/{resourceId}/import-preset`
**Formats**: `.json` (SillyTavern preset)

The preset import endpoint:

1. Accepts a **SillyTavern preset JSON** file.
2. Creates or replaces the draft data with the preset parameters.

Because presets are self-contained parameter sets (model settings, temperature, context size, etc.), import replaces the entire preset rather than merging field-by-field.

### World bundles

**Endpoint**: `POST /resources/{resourceId}/import-world`
**Formats**: `.zip` (World Simulation Engine package)

The world import endpoint:

1. Accepts a **WorldSE `.zip` package** containing world data, media, and configuration.
2. Extracts all images from the package and creates standalone **image resources** under your account, each linked back to the world bundle by reference.
3. Stores the world data as the draft's `worldData`.
4. Sets the world's cover image (if one is specified in the bundle) from the extracted media.

World images benefit from **S3 deduplication** — if an extracted image's SHA-256 already exists under your account, a new copy is not made.

After import, the world resource's metadata is updated:

- **Language** is inferred from the world's locale settings.
- **Tags** imported from the world are appended to existing tags (deduplication applied).
- **Description** follows the merge rule: existing description is kept; imported description fills only when empty.

## Importing from the UI

Each resource type has an import button on its editing page. Click import, select the file, and choose one of the supported formats. The system validates the file, extracts the data, and merges it into your draft.

## Constraints

| Constraint | Limit |
|---|---|
| Resource must exist | Import works on existing resources only (not at creation time) |
| File size — character cards | Limited by `RC_IMAGE_MAX_BYTES` (default 20 MiB) |
| File size — presets | Limited by `RC_PRESET_MAX_BYTES` (default 5 MiB) |
| File size — world bundles | Limited by `RC_WORLD_BUNDLE_MAX_BYTES` (default 100 MiB) |
| PNG card detection | Reads `tEXt` chunks: `ccv3` → V3, `chara` → V2 |
| Lorebook extraction from PNG | Requires the card's `character_book` field to be present |

## Tips and notes

> [!NOTE]
> **Import updates the timestamp.** After import, the resource's `updated_at` field is refreshed, placing it at the top of date-sorted lists.

> [!NOTE]
> **Draft vs release.** Import modifies the **draft only** — any existing published versions are untouched. You must publish a new version to release the import changes to readers.

> [!TIP]
> **Use import for cleanup.** If you have a buggy character card in SillyTavern, you can create a blank resource and import a known-good JSON or PNG version — the system will validate and convert the format for you.

> [!TIP]
> **PNG imports capture cover images automatically.** When importing a `.png` character card, the image file is stored as the resource's cover image, so you don't need to upload a separate thumbnail.

## API reference (for developers)

| Method | Endpoint | Accepts | Description |
|---|---|---|---|
| `POST` | `/resources/{id}/import-card` | `.json`, `.png` | Import / merge a character card |
| `POST` | `/resources/{id}/import-lorebook` | `.json`, `.png` | Import / merge a lorebook |
| `POST` | `/resources/{id}/import-preset` | `.json` | Import a SillyTavern preset |
| `POST` | `/resources/{id}/import-world` | `.zip` | Import a World Simulation Engine bundle |
