# SillyTavern Lore Books

## Overview

SillyTavern Lore Books are first-class resources in the Catalogue. You can upload, edit, version, fork, and publish lorebooks independently — or link them to character cards so the lorebook data travels with the character when published.

## How to Use

### Creating a Lorebook

A lorebook is a collection of **entries** that provide in-game context to the persona. Each catalogue lorebook can hold up to 50 entries. You can create lorebook draft content via the upload form or by importing from an existing SillyTavern lorebook.

The system automatically detects whether an uploaded JSON file uses the current **`lorebook_v3`** specification or a legacy **V2** format, and parses accordingly.

### Importing a Lorebook

You can import lorebook data from three sources:

- **Standalone JSON** — a complete SillyTavern V2 or V3 lorebook file.
- **Embedded in a character card JSON** — when you import a character card that includes a lorebook block, the Catalogue parses both the card and its lorebook.
- **Embedded in a PNG character card** — the Catalogue reads the lorebook data from the tEXt chunk alongside the card itself.

### Merging Behaviour

If you import a lorebook onto a resource that already has draft entries, the same merge strategy used for character cards applies:
- Existing entries are retained; new entries are appended.
- Dict-like fields are merged key-by-key.
- Missing values on the incoming data are filled from the existing draft.

To replace all content, clear the draft first.

### Linking from Character Cards

Every character card draft maintains a list of **linked lorebook references**. For each link you choose one of two modes:

| Mode | Behaviour |
|------|-----------|
| **Link Draft** | Live — the character card will always use the latest published content when the card itself is re-published. |
| **Link Release Version** | Locked — the character card preserves the exact state of the lorebook at the time of linking. |

When a character card is published, every linked lorebook is **merged into the compiled JSON** of the card. The publishing user does not need to export or download the lorebooks separately.

### Cover Image

A lorebook can have a cover image. Set one through the editor's **cover image selector**. The cover image must meet the standard image upload requirements (see the Images documentation).

### Forking

You can fork a published lorebook. A forked lorebook carries all of the source version's linked lorebook references forward, making it easy to build chains of lore-based expansions.

## Constraints

| Constraint | Limit |
|------------|-------|
| Maximum entries per lorebook | 50 |
| Maximum linked lorebooks per character card | 50 |
| Supported lorebook specifications | `lorebook_v3` (current), V2 (legacy, auto-detected) |
| Maximum cover image size | 20 MiB |

## Tips and Notes

- **Links are a double-edged sword.** When the published source lorebook changes, every character card that links to its *live* draft will reflect that change on their next publish. If you want stability, link a pinned release version instead.
- **Deletion protection.** A lorebook that is currently linked to a character card cannot be deleted from the catalogue. You must remove the link first.
- **PNG import convenience.** If your lorebook is embedded inside a PNG character card, one upload gives you both — perfect for sharing complete sets.
- **Versioning is automatic.** Every time you publish, a new immutable version is created and added to the version history — you can always roll back or diff back.
