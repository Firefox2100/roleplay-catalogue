# Forking Resources

**Forking** lets you create a derived version of any published resource — one that belongs to you, with an editable draft based on the original's latest release. Forks are the foundation for remixing, adapting, and improving community content under the catalogue's versioning system.

## Overview

When you fork a resource the system:

1. **Snapshots** the latest published version of the source.
2. **Creates a new resource** of the same type under your account.
3. **Initialises the editable draft** from the source version's data.

The fork is your own resource from the moment it's created — you can edit, relabel, or republish it without affecting the original.

## How to fork

### From the UI

Navigate to the detail page of any publishable resource version. Click the **Fork** button. A new resource is generated instantly and you are redirected to your new draft editor.

### From the API

Call the fork endpoint with the version ID you want to base your fork on:

```
POST /versions/{versionId}/fork
```

The source version must be readable by your account (public, authenticated, or private with your author/co-author permission).

## What gets copied

| Field | Source → Fork |
|---|---|
| Resource type | Identical (character, lorebook, preset, or world) |
| Draft data | Full snapshot of the version's data becomes your editable draft |
| `forkedFrom` | Records the original `resourceId` and `versionId` as a reference chain |
| Name | Default: **"Forked from [source name]"** — you can rename freely |
| Tags | Copied from the source release |
| Description | Copied from the source release |
| Linked lorebooks | Carried over into your draft at the exact same version references |
| Cover image | Copied beneath your account (see Dedup below) |
| Visibility | Always starts as **PRIVATE** (does not inherit the source version's visibility) |

### Cover image dedup

If the source version's release had a cover image, the fork finds an existing copy under your account by matching the **SHA-256 hash** of the image. If a matching image already exists in your storage, the fork reuses it. If no copy exists, the image is uploaded to your storage first, then referenced by the fork.

The fork's release artifact (once published) is stored under your own S3 bucket path:

```
releases/{your_resource_id}/{your_version_id}{extension}
```

## Fork behavior details

### Only published versions can be forked

The source version must have been published. Unpublished draft changes on the original resource are **not** included — only the latest released content is copied into your fork's draft.

### Fork visibility

The fork always starts as **PRIVATE**, regardless of how the source version was published. You may change the draft's visibility or any version's visibility at any time.

### Version chain on forking

After you publish your fork, the new version's `previousVersionId` points to your fork's prior version (if any). The `forkedFrom` field on the resource record preserves the link back to the original resource and original version indefinitely — this chain is never overwritten.

### Exporting a fork's draft

Before publishing, you can export the fork's draft exactly as any other resource:

- Characters: `.draft.json` or `.draft.png` (PNG export embeds the card data)
- Lorebooks: `.draft.json`
- Presets: `.draft.json`
- Worlds: `.draft.zip`

## Constraints

| Constraint | Limit |
|---|---|
| Resource types supportable | Character, Lorebook, Preset, World |
| Image resources | Not forkable (image data is inherently a single immutable upload) |
| Published versions only | Unpublished draft edits are not included |
| Fork naming | Default is auto-generated; can be changed freely |
| Tag merging on forks | Tags are copied as-is; no dedup against existing fork tags |

## Tips and notes

> [!TIP]
> **Start a fork from the version you want.** If a resource has multiple published versions, navigate to the specific version page and fork from there. The system forks the snapshot of that exact version, not the latest.

> [!NOTE]
> **Forks create a contribution trail.** The `forkedFrom` reference forms a directed acyclic graph across all resources. You can trace a forked resource back through its ancestors to find its original source, and forward to discover derivatives. This is displayed on the detail page.

> [!NOTE]
> **Linked lorebooks survive the fork unchanged.** If the source character referenced a lorebook at version `abc123`, your fork's draft starts with an identical reference to the same lorebook version. You can later update the lorebook link to point to a different version.

## API reference (for developers)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/versions/{versionId}/fork` | Create a new resource forked from the given version |
| `GET` | `/versions/draft/{resourceId}/download` | Export the fork's pre-publish draft |
| `GET` | `/versions/{versionId}/download` | Download the fork's published artifact |
