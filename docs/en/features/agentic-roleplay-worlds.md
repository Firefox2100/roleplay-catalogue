# DeepSeek Harness Agentic Roleplay Worlds

Roleplay Catalogue can store and publish a native world folder from the `dsh-agentic-roleplay` project. The transfer format is deliberately simple: zip the folder, upload it, then download and extract the same folder into a Harness installation.

The catalogue preserves the package rather than translating it into the WorldSE schema. This keeps project-specific files together and avoids a lossy conversion between the two world formats.

## Prepare the ZIP

The archive must contain one top-level folder. That folder must contain `world.json` directly inside it.

```text
harbour-world/
  world.json
  characters/
  locations/
  media/
    manifest.jsonl
    ...
```

Zip `harbour-world` itself, not only the files inside it. Do not add a second top-level folder or loose files beside it.

The importer checks the archive before storing it. It rejects unsafe paths, symbolic links, encrypted entries, duplicate or case-colliding paths, malformed UTF-8 JSON and JSONL, and archives that exceed the configured limits. Every file remains inside the ZIP. The catalogue does not execute package contents.

This validation covers the archive and document syntax. DeepSeek Harness remains responsible for validating the complete world model when it loads the folder.

## Upload and edit

Create a resource with the type **DeepSeek Harness agentic-roleplay world**, then open its editor and upload the ZIP. Uploading another ZIP replaces the draft package. Published releases are not changed.

The editor shows the package name, native version, author, folder name, file count, and compressed size. **Use package metadata** copies the native name and description into the catalogue fields and merges the native tags. You can keep different catalogue metadata if that makes the resource easier to find.

If `world.json` has no `id`, the importer adds one to the normalized package. If it names `cover_media_id`, the importer resolves that item through `media/manifest.jsonl` and creates a catalogue image for the cover.

## Publish and compare releases

Publishing stores an immutable copy of the normalized ZIP. Each release records its file name, byte size, and SHA-256 hash.

Release diffs use the indexed package manifest. They show changes to the native metadata and each file's path, size, and SHA-256 value. The catalogue does not attempt a semantic, line-by-line diff of the world's internal documents.

## Install a downloaded world

Download the chosen release, extract it, and place the resulting top-level folder in the `worlds/` directory used by your DeepSeek Harness agentic-roleplay installation. Keep the folder structure intact. Harness performs its own domain validation when the world is loaded.

## Forking

Forking starts a private resource from the selected published release. The fork receives a new world ID so it can live beside the source world in the same Harness installation. Its other package files are preserved, and its catalogue record keeps a reference to the source release.

## Limits

| Check | Default or rule |
|---|---|
| Compressed upload size | 100 MiB, configurable with `RC_DSH_WORLD_MAX_BYTES` |
| Expanded archive size | 512 MiB |
| Archive entries | 5,000 maximum |
| Layout | One top-level folder containing `world.json` |
| Folder name | 1 to 100 ASCII letters, digits, dots, underscores, or hyphens; first character must be alphanumeric |
| JSON | UTF-8 JSON and JSONL files must parse successfully |
| Cover formats | PNG, JPEG, WebP, GIF, or AVIF |

