# Versioning & Releases

Roleplay Catalogue uses a two-part model for publishable resources: one mutable draft and a history of immutable releases. Images are stored as uploaded resources and do not use the release workflow.

## Overview

Every character, lorebook, preset, WorldSE world, and agentic-roleplay world consists of:

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
4. For character cards, linked lorebook releases are snapshotted into the version's `linkedLorebooks` field. Publication is rejected if a link still points to a draft.
5. A packaged artifact (`.json` or `.png` for character cards, `.json` for lorebooks and presets, or `.zip` for worlds) is uploaded to S3-compatible storage at `releases/{resource_id}/{version_id}{extension}`.
6. A unified content diff is computed against the previous release, or an empty document for the first release. Native agentic-roleplay ZIPs are represented by their indexed metadata and file manifest, not by their raw binary bytes.

### Updating the draft

After publishing, the **draft continues to be editable**. You can change any field — text content, tags, description, linked lorebooks, cover image — without affecting previous versions. These changes accumulate until the next publish.

### Managing version visibility

Each version has its own `visibility` field, independent of the draft's visibility:

- Set to `PUBLIC`, `AUTHENTICATED`, or `PRIVATE` at publish time (defaults to the draft's visibility).
- Can be changed at any time after publishing without re-creating the version.

Only the author can update a version's visibility.

### Viewing version history

From a resource's detail page, you can select from the published versions. The API returns the newest version first. Each version records:

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
| Resource types that can be published | Character, Lorebook, Preset, WorldSE world, DeepSeek Harness agentic-roleplay world |
| Image resource versions | Not separately publishable (image data is inherently immutable once uploaded) |
| Co-authors | Can edit the draft but cannot publish or delete versions |
| Deleting a resource | Only resources without any published versions can be deleted |

## Lorebook snapshotting

When you link a lorebook to a character:

- **As a draft** (`versionId: null` in `linkedLorebooks`): Useful while editing, but the character cannot be published until you select a lorebook release.
- **As a pinned release** (`versionId` set to a specific version ID): The character locks onto that exact version. This is useful for preserving compatibility with a specific lorebook revision.

On publish, the system verifies every pinned lorebook release and records its name, author, and version in the character snapshot.

## Tips and notes

> [!TIP]
> **Version labels are user-facing.** Use semantic versions like `1.0.0`, `1.1.0`, or `v2.3` so users can easily identify the latest release.

> [!NOTE]
> The content diff (`contentDiff`) stores a unified diff of the complete rendered release text — character card content *plus* any merged linked lorebook content. This lets you browse changes between versions visually, similar to `git log --diff`.

> [!NOTE]
> **Artifacts are immutable and versioned by their UUIDs.** The S3 key `releases/{resource_id}/{version_id}{extension}` means you can always re-download a specific version, even if later versions overwrite the name.
