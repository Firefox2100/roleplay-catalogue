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

### DeepSeek Harness Agentic Roleplay Worlds

Upload a native `dsh-agentic-roleplay` world folder as a ZIP and publish install-ready releases without converting the package to WorldSE. The catalogue indexes the package for metadata, cover handling, and file-manifest diffs while leaving full world-model validation to Harness.

- [Detailed guide: Agentic Roleplay Worlds](features/agentic-roleplay-worlds.md)

### Versioning & Releases

Characters, lorebooks, presets, and both world formats use a draft and release workflow. The draft remains editable; publishing creates an immutable snapshot with its own visibility, content diff, and stored artifact. Images are uploaded as immutable resources and are not published separately.

- [Detailed guide: Versioning](features/versioning.md)

### Forking

Fork a readable published character, lorebook, preset, or world release to create a private draft under your account. The new resource keeps its source reference, and reusable cover images are matched by SHA-256 within the fork owner's library.

- [Detailed guide: Forking](features/forking.md)

### Collaborative Editing

Authors invite co-authors to edit a resource's draft. Co-authors can upload data, change metadata, and link lorebooks; only the author can publish or delete.

- [Detailed guide: Collaborative Editing](features/collaborative-editing.md)

### Search & Filtering

MongoDB text search, tag / type / author filtering, pagination, tag autocomplete, and recent or popular sorting.

Resource cards and detail pages also show anonymous view and download counts. Opening a detail page records a view. Downloading through the application or creating a signed download link records a download.

- [Detailed guide: Search & Filtering](features/search-and-filtering.md)

### Importing Resources

Import existing SillyTavern content, WorldSE bundles, and native agentic-roleplay world ZIPs. Character and lorebook imports merge with their drafts; presets and native agentic-world ZIPs replace the type-specific draft payload.

- [Detailed guide: Importing Resources](features/importing-resources.md)
