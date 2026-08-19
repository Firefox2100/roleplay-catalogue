# Versioning & Releases

The Roleplay Catalogue uses a **two-tier model** for every resource (except images): a mutable draft and one or more immutable, versioned releases. This design lets you iterate on your content while keeping a stable history of every published revision.

## Overview

Every character, lorebook, preset, and world resource consists of:

- **Draft** — the editable payload that you modify over time. The draft has its own metadata (name, description, tags, visibility) that may change independently of any published version.
- **Version (Release)** — a point-in-time snapshot of the draft's data and metadata. Versions are immutable; once created, the underlying content cannot be changed. Each version carries its own visibility setting.

### Draft vs Version at a glance

| Aspect | Draft | Published Version |
|---|---|---|
| Mutability | Fully editable by author / co-authors | Immutable data; frozen at publish time |
| Data record | Lives in type-specific collection with `resourceVersionId: null` | Lives in a separate record with `resourceVersionId` set = version ID |
| Metadata | Updated live as you edit | Snapshot captured at moment of publish |
| Visibility | Controlled by `Resource.metadata.visibility` | Independent; controllable via PATCH endpoint even after publish |
| Who creates | Author / co-author during editing | Author only (via Publish action) |

## How versioning works

### Creating a draft

When you create a resource through the UI or API, an empty draft record is created in the appropriate type-specific data collection. This draft is editable immediately; no version exists yet.

### Publishing a release

To publish, the author clicks the **Publish** button (or calls the publish endpoint). During publication:

1. The current draft data is **copied** (not moved) into a new immutable document with a non-null `resourceVersionId`.
2. A new **version record** is created with an incremented `versionNumber` starting at `1`.
3. The resource's **metadata is frozen** at that moment — any subsequent draft edits do not retroactively change previous version metadata.
4. For character cards, linked lorebooks are **snapshoted** into the version's `linked_lorebooks` field. If a lorebook was linked as a draft, it captures the latest published release of that lorebook instead.
5. A packaged **artifact** (e.g. `.json` or `.png` for character cards, `.json` for lorebooks/presets, `.zip` for worlds) is uploaded to S3 storage at `releases/{resource_id}/{version_id}{extension}`.
6. The artifact's **content diff** (a git-style unified diff) is computed against the previous version's rendered content — or against an empty document for the first release.

### Updating the draft

After publishing, the **draft continues to be editable**. You can change any field — text content, tags, description, linked lorebooks, cover image — without affecting previous versions. These changes accumulate until the next publish.

### Managing version visibility

Each version has its own `visibility` field, independent of the draft's visibility:

- Set to `PUBLIC`, `AUTHENTICATED`, or `PRIVATE` at publish time (defaults to the draft's visibility).
- Can be changed at any time after publishing without re-creating the version.

Only the author can update a version's visibility.

### Viewing version history

From a resource's detail page, you can see all published versions sorted by `versionNumber` in **ascending order**. Each entry shows:

- Version number and label (e.g. "1.0.0")
- Publication date
- Visibility (public, authenticated-only, or private)
- File size and content hash
- Link download

Clicking a version displays its frozen metadata and linked lorebook references.

## Constraints

| Constraint | Limit |
|---|---|
| Version label (display text) | Max 100 characters, must not be blank |
| Resource types that can be published | Character, Lorebook, Preset, World |
| Image resource versions | Not separately publishable (image data is inherently immutable once uploaded) |
| Co-authors | Can edit the draft but cannot publish or delete versions |
| Deleting a resource | Only resources without any published versions can be deleted |

## Lorebook snapshotting

When you link a lorebook to a character:

- **As a draft** (`versionId: null` in `linkedLorebooks`): The character always references the lorebook's latest published version at release time. If the lorebook had no releases yet, the draft itself is used.
- **As a pinned release** (`versionId` set to a specific version ID): The character locks onto that exact version. This is useful for preserving compatibility with a specific lorebook revision.

On every publish, the system walks the lorebook links and creates the appropriate snapshot.

## Tips and notes

> [!TIP]
> **Version labels are user-facing.** Use semantic versions like `1.0.0`, `1.1.0`, or `v2.3` so users can easily identify the latest release.

> [!NOTE]
> The content diff (`contentDiff`) stores a unified diff of the complete rendered release text — character card content *plus* any merged linked lorebook content. This lets you browse changes between versions visually, similar to `git log --diff`.

> [!NOTE]
> **Artifacts are immutable and versioned by their UUIDs.** The S3 key `releases/{resource_id}/{version_id}{extension}` means you can always re-download a specific version, even if later versions overwrite the name.

## API reference (for developers)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/versions/{resourceId}` | Create a new release from the current draft |
| `PATCH` | `/versions/{versionId}/visibility` | Change visibility of a published version |
| `GET` | `/versions/resource/{resourceId}` | List all published versions (ascending) |
| `GET` | `/versions/{versionId}` | Get a specific version's metadata |
| `GET` | `/versions/{versionId}/data` | Get the frozen payload for a version |
| `GET` | `/versions/{versionId}/download` | Download the packaged artifact |
| `GET` | `/versions/{versionId}/signed-download` | Get a signed S3 URL for offline access |
| `GET` | `/versions/draft/{resourceId}/download` | Export the current draft as a `.draft.json` file |
