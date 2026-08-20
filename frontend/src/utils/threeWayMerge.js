function isEqual(a, b) {
  if (a === b) return true
  if (typeof a !== typeof b || a === null || b === null || typeof a !== 'object') return false
  if (Array.isArray(a) !== Array.isArray(b)) return false
  if (Array.isArray(a)) {
    return a.length === b.length && a.every((item, index) => isEqual(item, b[index]))
  }
  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  return keysA.length === keysB.length && keysA.every((key) => isEqual(a[key], b[key]))
}

// Merges an array of objects (e.g. lorebook entries) by matching elements on `keyField`,
// so an edit to one entry doesn't flag the whole array as a single conflict.
function mergeKeyedArray(base, local, remote, keyField) {
  const byKey = (list) => new Map(list.map((item) => [item[keyField], item]))
  const baseMap = byKey(base)
  const localMap = byKey(local)
  const remoteMap = byKey(remote)
  const allKeys = [...new Set([...baseMap.keys(), ...localMap.keys(), ...remoteMap.keys()])]

  const merged = []
  const conflicts = {}
  for (const key of allKeys) {
    const baseItem = baseMap.get(key)
    const localItem = localMap.get(key)
    const remoteItem = remoteMap.get(key)

    if (isEqual(localItem, remoteItem)) {
      if (localItem !== undefined) merged.push(localItem)
    } else if (isEqual(localItem, baseItem)) {
      if (remoteItem !== undefined) merged.push(remoteItem)
    } else if (isEqual(remoteItem, baseItem)) {
      if (localItem !== undefined) merged.push(localItem)
    } else {
      conflicts[key] = { base: baseItem, local: localItem, remote: remoteItem }
      if (localItem !== undefined) merged.push(localItem)
    }
  }
  return { merged, conflicts }
}

// Shallow per-key three-way merge: a field changed on only one side (relative to `base`)
// merges automatically; a field changed differently on both sides is reported as a conflict,
// tentatively defaulting to the local value until the caller resolves it.
//
// `keyedArrayFields` maps a top-level field name to the id field its array elements should be
// matched on (e.g. `{ entries: 'uid' }` for lorebook entries), so per-entry edits merge instead
// of the whole array being flagged as one conflict.
export function threeWayMerge(base, local, remote, keyedArrayFields = {}) {
  const keys = new Set([...Object.keys(base ?? {}), ...Object.keys(local ?? {}), ...Object.keys(remote ?? {})])
  const merged = {}
  const conflicts = {}

  for (const key of keys) {
    const baseValue = base?.[key]
    const localValue = local?.[key]
    const remoteValue = remote?.[key]

    if (isEqual(localValue, remoteValue)) {
      merged[key] = localValue
      continue
    }
    if (isEqual(localValue, baseValue)) {
      merged[key] = remoteValue
      continue
    }
    if (isEqual(remoteValue, baseValue)) {
      merged[key] = localValue
      continue
    }
    if (keyedArrayFields[key] && Array.isArray(baseValue) && Array.isArray(localValue) && Array.isArray(remoteValue)) {
      const result = mergeKeyedArray(baseValue, localValue, remoteValue, keyedArrayFields[key])
      merged[key] = result.merged
      if (Object.keys(result.conflicts).length > 0) conflicts[key] = { entries: result.conflicts }
      continue
    }
    conflicts[key] = { base: baseValue, local: localValue, remote: remoteValue }
    merged[key] = localValue
  }

  return { merged, conflicts }
}
