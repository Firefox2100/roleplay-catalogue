# Roleplay Catalogue

Roleplay Catalogue is an open-source, self-hosted library for SillyTavern and related roleplay resources. It is designed for individuals and groups that want to keep control of their collection, publishing rules, and infrastructure.

## License and Disclaimer   

Roleplay Catalogue is licensed under [GPL v3](https://www.gnu.org/licenses/gpl-3.0.en.html). You may use, modify, and distribute it subject to that licence. The software is provided without warranty; operators and users remain responsible for how they deploy and use it.

This software is provided as a hosting platform solution, with no included content or filtering on the content. The party deploying the software is responsible for the content and its compliance with applicable laws and regulations. The authors and contributors of this software cannot be held liable for any legal issues or disputes that may arise from the content hosted on the platform.

## Features

The catalogue supports readers discovering content, authors maintaining it, and administrators operating the service.

### Character Cards

Create, upload, and download character cards in SillyTavern's V3 format (V2 cards auto-convert on import). Cards can include embedded lorebooks, PNG cover images, and up to 50 linked lorebooks from the catalogue. Fork existing cards to make derivative versions.

- [Detailed guide: Character Cards](features/character-cards.md)

### Lore Books

Upload, version, and link lorebooks as first-class resources. Lorebooks are self-contained and can be linked from character cards (live draft or pinned release) so the definition travels with the character on publish.

- [Detailed guide: Lore Books](features/lore-books.md)

### Chat Presets

SillyTavern generation presets (temperature, stop tokens, repetition penalty, etc.) stored and shared as JSON. Fork presets to tweak settings for your own characters.

- [Detailed guide: Chat Presets](features/chat-presets.md)

### Images & Covers

Upload image resources (PNG, JPEG, WebP, GIF). Assign cover images to character cards, lorebooks, and worlds. Images are immutable after publish and deduplicated by SHA-256 across forks.

- [Detailed guide: Images](features/images.md)

### World Bundles

Upload and share WorldSE-compatible `.zip` bundles. Embedded images are extracted into the catalogue. Fork worlds to derive new game settings from existing designs.

- [Detailed guide: World Bundles](features/worlds.md)

### Versioning & Releases

Every resource follows a **draft → release** workflow. The draft is editable at any time; releasing creates an immutable snapshot with its own visibility, content diff, and S3 artifact.

- [Detailed guide: Versioning](features/versioning.md)

### Forking

Fork any published version to create a derived resource under your account. Cover images are deduplicated, lorebooks carry over, and the fork starts private for safe editing before share.

- [Detailed guide: Forking](features/forking.md)

### Collaborative Editing

Authors invite co-authors to edit a resource's draft. Co-authors can upload data, change metadata, and link lorebooks; only the author can publish or delete.

- [Detailed guide: Collaborative Editing](features/collaborative-editing.md)

### Search & Filtering

Full-text search via MongoDB Community Search, tag / type / author filtering, pagination, and tag-autocomplete.

Resource cards and detail pages also show anonymous view and download counts. Opening a detail page records a view. Downloading through the application or creating a signed download link records a download.

- [Detailed guide: Search & Filtering](features/search-and-filtering.md)

### Importing Resources

Import existing SillyTavern content — character cards (JSON / PNG), lorebooks, presets, and world bundles. The catalogue **merges** incoming data into drafts to avoid overwriting hand-crafted edits.

- [Detailed guide: Importing Resources](features/importing-resources.md)
