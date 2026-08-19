# SillyTavern Chat Presets

## Overview

The Roleplay Catalogue stores and shares **SillyTavern chat presets** — model-specific generation configurations that define things like temperature, max tokens, stop sequences, repetition penalty, and other sampler settings. Presets let you share your favourite generation configurations with others and switch between different "styles" of model behaviour quickly.

Presets follow the standard SillyTavern JSON preset format and are first-class catalogue resources. They appear in search results, support tags and visibility settings, can be forked, downloaded as JSON, and viewed with language labels.

## How to Use

### Uploading a Preset

1. Navigate to the preset upload area in the Catalogue editor.
2. Select a `.json` file in SillyTavern preset format.
3. Provide a **name** (required, up to 200 characters) and an optional **description** (up to 10,000 characters).
4. Optionally add **tags**, set a **visibility** level, and choose a **language**.
5. Submit to upload.

The uploaded JSON is parsed and stored as the preset resource's draft data.

### JSON Preview

Every published preset includes a JSON preview. You can review the full generation settings displayed in an expandable panel without downloading the package.

### Exporting a Preset

1. Open the preset detail page.
2. Click the **Export** button to download the preset as a `.json` file.

Packets exports are available for four resource types: characters, lorebooks, presets, and worlds.

### Creating a Fork

1. Open any published preset.
2. Choose **Fork** from the preset actions menu.
3. The Catalogue creates a new preset resource that contains all the configuration data of the source at the point you forked.
4. Edit the settings to your liking. Changes appear in the fork, leaving the original untouched.

### Searching and Filtering

Presets appear in general search results alongside characters, lorebooks, and worlds. The same filtering mechanisms apply:

- **Tag filtering** — search by tags on the preset.
- **Visibility filter** — public and unlisted presets are shown in browse views; private ones only to the owning user.
- **Language filter** — presets carry a language label (English or Chinese Simplified) based on their metadata.

### Import Behaviour

When you import a SillyTavern preset JSON onto an existing resource that already has draft data, the imported JSON **overwrites** the draft with the uploaded content. To keep the existing draft while testing changes, download the current draft first.

## Constraints

| Constraint | Limit |
| --- | --- |
| Maximum file size (`preset_max_bytes`) | 5 MiB (5,242,880 bytes) |
| Preset name | Required, up to 200 characters |
| Preset description | Optional, up to 10,000 characters |
| Accepted format | SillyTavern preset JSON |
| Cover image | Not supported for presets |
| Language | Optional, set per preset |
| Exportable resource types | Characters, lorebooks, presets, and worlds only |

## Tips and Notes

- **Small but powerful.** Presets control how the model behaves during generation. Consider creating presets for different characters or roles — a "creative" preset with higher temperature, and a "deterministic" preset for roleplay that needs consistency.
- **Fork before you tweak.** Forking a published preset gives you a clean starting point. Any changes you make go into the fork, leaving the original untouched.
- **JSON-only export.** Only the four listed resource types support public export. Use the export function rather than the raw API to get a usable `.json` file.
- **Import overwrites.** Importing a new JSON file replaces the draft data entirely. Download the existing draft first if you might want to reference it later.
- **No cover image.** Unlike characters and worlds, presets do not support cover images. Use descriptive names and tags to help users discover your preset.
