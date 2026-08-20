# SillyTavern Character Cards

## Overview

The Roleplay Catalogue uses SillyTavern's character card format as its core content type. Whether you're creating a new character from scratch or uploading an existing card, the Catalogue preserves compatibility with SillyTavern's widely used V2 and V3 formats. A character card in the Catalogue stores draft data, maintains a full version history, and can link up to 50 lorebooks from the catalogue.

## How to Use

### Creating or Uploading a Card

Upload your character card as a **JSON file** (V2 or V3) or as a **PNG file** that contains an embedded SillyTavern card in its `tEXt` chunks. The Catalogue will detect and parse whichever format you provide.

On publish, the Catalogue produces a complete, self-contained character card: any linked lorebooks are merged directly into the output JSON so the file can be used in SillyTavern without dependencies.

### Importing a Card that Already Exists

If you import data onto a character card that already has draft values, the system **merges** the incoming data with what's already on file:
- **Arrays** (such as `messages`, `post_history`, or `creator_notes`) are concatenated.
- **Objects/dicts** are merged key-by-key.
- **Missing fields** in the incoming data are filled in from the existing draft.
- Fields that exist in the draft but not in the incoming data are left unchanged.

### Extracting from PNG

If you upload a PNG character card, the Catalogue reads the embedded JSON from the `tEXt` chunk and sets the card's **cover image automatically**.

### Forking a Release

You can fork any published version of a character card. A fork creates a derived card whose displayed name starts with **"Forked from …"**. The `character_version` field of the new resource carries over the version label from the card you forked.

### Draft Data

You can export your draft data independently of the main card using the **Export Draft** action on the editor page. This produces:
- **`.draft.json`** — the raw SillyTavern card data.
- **`.draft.png`** — a PNG featuring the draft card embedded in its `tEXt` chunks, suitable for direct use with SillyTavern.

### Publishing Metadata

When you publish a card, the following metadata items are appended into the SillyTavern card output:
- **Tags** (from the Catalogue resource entry)
- **Description** (from the Catalogue resource entry)

The creator name defaults to your display name when you publish.

### Linking Lorebooks

A character card can have up to **50 linked lorebooks**. Links can be:
- A **draft** of a lorebook (live — it follows whatever edits are made until the next publish).
- A **pinned release version** of a lorebook (locked at the point you linked).

## Constraints

| Constraint | Limit |
|------------|-------|
| Maximum upload size | 20 MiB (20 × 1024 × 1024 bytes) |
| Linked lorebooks | Up to 50 per character card |
| Supported formats | JSON (V2 / V3), PNG with embedded JSON |
| Forked name prefix | "Forked from" |

## Tips and Notes

- **PNG imports are fast.** Uploading a SillyTavern PNG lets you skip the JSON step and gets your cover image for free.
- **Merged lorebooks = portable cards.** When you publish, linked lorebooks are baked into the output JSON. This means your character card always contains its full definition, regardless of whether the linked lorebooks still exist in the catalogue.
- **Careful when overwriting.** Since merge is additive (arrays concatenate), re-importing the same JSON multiple times will duplicate entries. Use "Replace" or clear the draft before re-importing identical content.
- **Version tracking.** The `character_version` field is not just cosmetic — it's part of the serialized card data so you can reference it in-game or in lore.
