# Images & Cover Images

## Overview

The Roleplay Catalogue supports two distinct roles for images:

- **Cover images** — visual thumbnails attached to character cards, lorebooks, presets, and world bundles. These are what visitors see in search results, on resource cards, and in listing pages.
- **Standalone images** — independent image resources that live in the catalogue on their own, with the same capabilities (name, description, tags, visibility, language) as every other resource type.

Every image stored in the Catalogue is also a full **image resource**. It can be named, described, tagged, set to a specific visibility and language, and tracked through version history — just like character cards or lorebooks.

## How to Use

### Uploading an Image

1. Navigate to the image upload area in the Catalogue.
2. Select a file in one of the supported formats (PNG, JPEG, WebP, or GIF).
3. The upload creates an **image resource** automatically and publishes **Version 1** of that resource.
4. After publish the version is immutable — it will not change. To replace an image, upload a new file and select it as the cover where needed.

**Maximum upload size:** 20 MiB.

### Setting a Cover Image on a Character, Lorebook, or World

1. Open the resource editor (e.g. the character card editor).
2. Locate the **"Select cover image"** control.
3. Browse your uploaded images and choose one.
4. Save the resource — the cover reference now points to the latest published version of the selected image.

**Note:** An image must have at least one published version before it can be selected as a cover image.

### Cover Images Extracted During Character Import

When you import a SillyTavern character card via PNG, the Catalogue automatically reads the `[cover_image]` field from the character data and the embedded tEXt chunk. If a cover image is found in the PNG it is extracted, stored as an independent image resource, and set as the card's cover automatically.

### Downloading and Serving

- Every image resource provides a **signed download URL** that expires after **120 seconds**.
- Public images served from the Catalogue are cacheable with `Cache-Control: public, max-age=31536000, immutable` (one year), which is safe because images are immutable once published.

### Deleting an Image

- Images can be deleted using `force=true` even if they are currently referenced as cover images by one or more resources. References are simply cleared.

### Forking Resources with Cover Images

When a character card, lorebook, preset, or world is forked and it has a cover image:

- The Catalogue checks whether a copy of that image already exists for the fork author (deduplicated by SHA-256 hash).
- If an identical copy already exists, it is reused.
- Otherwise, a new copy is uploaded under the fork author, and the fork's cover points to that new copy.

## Constraints

| Constraint | Value |
| --- | --- |
| Supported formats | PNG, JPEG, WebP, GIF |
| Maximum file size (`image_max_bytes`) | 20 MiB |
| Signed URL expiry (`signed_url_expiry`) | 120 seconds |
| Cover image immutability | Versions cannot be modified after publish |
| Image must be published | At least one version must exist before serving as a cover |

## Tips and Notes

- **Replaces are additive.** Uploading a new version of a cover image does not delete the old one — both versions remain in the catalogue. This lets you roll back if needed.
- **Use standalone images for reuse.** If you know the same art will serve as the cover for multiple characters or worlds, upload it once as a standalone image and reference it from each resource.
- **Signed URLs are short-lived.** If you need to embed an image publicly (e.g. in an email or blog post), use the direct public URL endpoint rather than a signed download URL.
- **Chunk-based extraction.** Cover images embedded in SillyTavern PNG cards are pulled from the `tEXt` ID chunk (`[cover_image]`). If the card is a PNG without this chunk, import will still create the character resource but no cover image will be attached.
- **Cache-friendly.** Because published images never change, their one-year immutable cache headers are safe and help reduce bandwidth costs for visitors.
