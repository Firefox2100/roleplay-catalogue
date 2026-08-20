// Maps a full Resource (from GET/PUT, or a 412 conflict's `current`) down to the same flat
// shape as the ResourceUpdateRequest body, so `updateResource` calls and threeWayMerge can
// compare `base`/`local`/`remote` field by field. `linkedLorebooks` is intentionally excluded:
// the backend rejects it for any resource type other than a character, so only
// CharacterEditorPage adds it on top of this, and only for itself.
export function resourceToMetadataPayload(resource) {
  return {
    name: resource.metadata.name,
    description: resource.metadata.description,
    language: resource.metadata.language,
    visibility: resource.metadata.visibility,
    tags: resource.metadata.tags ?? [],
  }
}
