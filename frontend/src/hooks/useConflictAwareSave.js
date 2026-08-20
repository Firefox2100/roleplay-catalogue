import { useState } from 'react'
import { threeWayMerge } from '../utils/threeWayMerge.js'

// Wraps one ETag-guarded save call (updateResource / saveResourceData / updateImageMetadata)
// with 3-way-merge conflict handling. `apiSave(payload, expectedRevision)` must be one of the
// api/resources.js functions bound to its resource id, so it rejects with an ApiError carrying
// `status === 412` and `body.detail.current` (the server's current object) when the revision
// sent as If-Match is stale.
//
// `extractComparable` maps a full server object (a Resource or a ResourceDataDocument) down to
// the same flat shape as the request payload, so `base`/`local`/`remote` are comparable field by
// field. `onSaved` fires with the full server response after every successful save, including
// one that resolved a conflict, so the caller only needs one state-update path.
export function useConflictAwareSave({ apiSave, extractComparable, extractRevision, keyedArrayFields, onSaved }) {
  const [conflict, setConflict] = useState(null)
  const [isRetrying, setIsRetrying] = useState(false)

  async function attempt(localPayload, base, revision) {
    try {
      const saved = await apiSave(localPayload, revision)
      setConflict(null)
      onSaved(saved)
      return saved
    } catch (error) {
      if (error?.status !== 412 || !error.body?.detail?.current) throw error
      const remoteFull = error.body.detail.current
      const remote = extractComparable(remoteFull)
      const { merged, conflicts } = threeWayMerge(base, localPayload, remote, keyedArrayFields)
      if (Object.keys(conflicts).length === 0) {
        // Everything merged automatically; retry right away against the fresh revision.
        return attempt(merged, remote, extractRevision(remoteFull))
      }
      setConflict({ remote, remoteFull, merged, conflicts })
      return null
    }
  }

  async function retry(resolvedPayload) {
    if (!conflict) return null
    setIsRetrying(true)
    try {
      return await attempt(resolvedPayload, conflict.remote, extractRevision(conflict.remoteFull))
    } finally {
      setIsRetrying(false)
    }
  }

  function cancel() {
    setConflict(null)
  }

  return { conflict, isRetrying, attempt, retry, cancel }
}
