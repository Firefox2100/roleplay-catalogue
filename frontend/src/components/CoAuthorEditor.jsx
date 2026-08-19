import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { addCoAuthor, getResource, removeCoAuthor } from '../api/resources.js'

// Resolves and manages its own co-author list rather than trusting the parent's
// `resource` prop: most editor mutations (save, publish, cover changes, ...) only
// ever get back a bare Resource (author/co-author IDs, no usernames) and would
// otherwise blank out a previously-resolved display.
export function CoAuthorEditor({ resourceId, authorId, currentUserId, onChange }) {
  const { t } = useTranslation()
  const [coAuthors, setCoAuthors] = useState([])
  const [isLoaded, setIsLoaded] = useState(false)
  const [username, setUsername] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [removingId, setRemovingId] = useState('')
  const [error, setError] = useState('')

  const isOwner = currentUserId === authorId

  function applyResource(resource) {
    setCoAuthors((resource.coAuthorIds ?? []).map((id, index) => (
      { id, username: resource.coAuthorUsernames?.[index] ?? id }
    )))
    onChange?.(resource)
  }

  useEffect(() => {
    let active = true
    getResource(resourceId).then((resource) => {
      if (active) applyResource(resource)
    }).catch(() => {}).finally(() => { if (active) setIsLoaded(true) })
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resourceId])

  if (isLoaded && !isOwner && coAuthors.length === 0) return null

  async function submitAdd() {
    if (!username.trim()) return
    setIsAdding(true)
    setError('')
    try {
      await addCoAuthor(resourceId, username.trim())
      applyResource(await getResource(resourceId))
      setUsername('')
    } catch {
      setError(t('editor.coAuthorAddFailed'))
    } finally {
      setIsAdding(false)
    }
  }

  async function remove(coAuthorId) {
    setRemovingId(coAuthorId)
    setError('')
    try {
      await removeCoAuthor(resourceId, coAuthorId)
      // A co-author removing themselves loses read access to a private draft,
      // so re-fetching may 404; fall back to trimming the known list locally.
      const resource = await getResource(resourceId).catch(() => null)
      if (resource) {
        applyResource(resource)
      } else {
        setCoAuthors((current) => current.filter((coAuthor) => coAuthor.id !== coAuthorId))
      }
    } catch {
      setError(t('editor.coAuthorRemoveFailed'))
    } finally {
      setRemovingId('')
    }
  }

  return (
    <div className="co-author-editor">
      <label>{t('editor.coAuthors')}</label>
      <p className="field-help">{t('editor.coAuthorsHelp')}</p>
      <div className="tag-editor-input co-author-chips">
        {coAuthors.length === 0 && <span className="empty-releases">{t('editor.noCoAuthors')}</span>}
        {coAuthors.map((coAuthor) => (isOwner || coAuthor.id === currentUserId) ? (
          <span className="tag-chip" key={coAuthor.id}>{coAuthor.username}
            <button type="button" disabled={removingId === coAuthor.id}
              aria-label={coAuthor.id === currentUserId
                ? t('editor.leaveCoAuthor')
                : t('editor.removeCoAuthor', { username: coAuthor.username })}
              onClick={() => remove(coAuthor.id)}>×</button>
          </span>
        ) : (
          <span className="tag-chip" key={coAuthor.id}>{coAuthor.username}</span>
        ))}
      </div>
      {isOwner && (
        // A plain div, not a <form>: this component is always rendered inside the
        // page's own <form>, and nested <form> elements are invalid HTML that
        // silently breaks submit handling.
        <div className="co-author-add">
          <input value={username} maxLength={100} disabled={isAdding}
            placeholder={t('editor.coAuthorUsernamePlaceholder')}
            onChange={(event) => setUsername(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') { event.preventDefault(); submitAdd() }
            }} />
          <button type="button" disabled={isAdding || !username.trim()} onClick={submitAdd}>
            {isAdding ? t('editor.addingCoAuthor') : t('editor.addCoAuthor')}
          </button>
        </div>
      )}
      {error && <p className="editor-message error" role="alert">{error}</p>}
    </div>
  )
}
