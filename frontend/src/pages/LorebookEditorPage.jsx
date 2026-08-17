import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  deleteResource, draftDownloadUrl, getResource, getResourceData, importLorebook, listResources,
  listResourceVersions, publishResource, saveResourceData, selectCharacterCover,
  updateResource, updateVersionVisibility, uploadCharacterCover,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { TagEditor } from '../components/TagEditor.jsx'


const EMPTY_BOOK = {
  scan_depth: '', token_budget: '', recursive_scanning: false, extensions: {},
}


function newEntry(index = 0) {
  return {
    localId: crypto.randomUUID(), keys: '', secondary_keys: '', content: '', name: '',
    comment: '', enabled: true, insertion_order: index, use_regex: false, constant: false,
    selective: false, case_sensitive: false, position: '', priority: '', id: null, extensions: {},
  }
}


function optionalNumber(value) {
  return value === '' || value === null || value === undefined ? null : Number(value)
}


export function LorebookEditorPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isLoading: isAuthLoading } = useAuth()
  const importInput = useRef(null)
  const imageInput = useRef(null)
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [resourceFields, setResourceFields] = useState({ name: '', description: '', visibility: 'private', tags: [] })
  const [book, setBook] = useState(EMPTY_BOOK)
  const [entries, setEntries] = useState([])
  const [versions, setVersions] = useState([])
  const [availableImages, setAvailableImages] = useState([])
  const [coverImageId, setCoverImageId] = useState(resource?.coverImageResourceId ?? '')
  const [isCoverPickerOpen, setIsCoverPickerOpen] = useState(false)
  const [isPublishOpen, setIsPublishOpen] = useState(false)
  const [releaseVersion, setReleaseVersion] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return undefined
    let active = true
    const resourceRequest = resource ? Promise.resolve(resource) : getResource(resourceId)
    Promise.all([
      resourceRequest,
      getResourceData(resourceId).catch((requestError) => (
        requestError.status === 404 ? null : Promise.reject(requestError)
      )),
      listResourceVersions(resourceId),
    ]).then(([loadedResource, draft, loadedVersions]) => {
      if (!active) return
      if (loadedResource.resourceType !== 'sillytavern/lorebook') throw new Error('Wrong type')
      setResource(loadedResource)
      setResourceFields({
        name: loadedResource.metadata.name,
        description: loadedResource.metadata.description,
        visibility: loadedResource.metadata.visibility,
        tags: loadedResource.metadata.tags ?? [],
      })
      setCoverImageId(loadedResource.coverImageResourceId ?? '')
      setVersions(loadedVersions)
      if (draft) {
        const data = draft.data
        setBook({
          scan_depth: data.scan_depth ?? '', token_budget: data.token_budget ?? '',
          recursive_scanning: data.recursive_scanning ?? false,
          extensions: data.extensions ?? {},
        })
        setEntries((data.entries ?? []).map((entry, index) => ({
          ...newEntry(index), ...entry,
          keys: entry.keys?.join(', ') ?? '',
          secondary_keys: entry.secondary_keys?.join(', ') ?? '',
          name: entry.name ?? '', comment: entry.comment ?? '',
          priority: entry.priority ?? '', position: entry.position ?? '',
        })))
      }
    }).catch(() => { if (active) setError(t('lorebookEditor.loadFailed')) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [resource, resourceId, t, user])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ resourceType: 'core/image', author: user.username, limit: 100 })
      .then((page) => { if (active) setAvailableImages(page.items) }).catch(() => {})
    return () => { active = false }
  }, [user])

  if (!isAuthLoading && !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (isAuthLoading || isLoading) return <div className="page-loading">{t('lorebookEditor.loading')}</div>

  function updateEntry(localId, field, value) {
    setEntries((current) => current.map((entry) => (
      entry.localId === localId ? { ...entry, [field]: value } : entry
    )))
  }

  function makeDraftData() {
    return {
      name: null,
      description: null,
      scan_depth: optionalNumber(book.scan_depth),
      token_budget: optionalNumber(book.token_budget),
      recursive_scanning: book.recursive_scanning,
      extensions: book.extensions ?? {},
      entries: entries.map((entry) => {
        const saved = {
          ...entry,
          keys: entry.keys.split(',').map((key) => key.trim()).filter(Boolean),
          secondary_keys: entry.secondary_keys
            ? entry.secondary_keys.split(',').map((key) => key.trim()).filter(Boolean) : null,
          insertion_order: Number(entry.insertion_order),
          priority: optionalNumber(entry.priority),
          position: entry.position || null,
        }
        delete saved.localId
        return saved
      }),
    }
  }

  async function persistDraft() {
    const updated = await updateResource(resourceId, resourceFields)
    setResource(updated)
    await saveResourceData(resourceId, makeDraftData())
  }

  async function save(event) {
    event.preventDefault()
    setBusy('save'); setError(''); setMessage('')
    try { await persistDraft(); setMessage(t('lorebookEditor.saved')) }
    catch { setError(t('lorebookEditor.saveFailed')) }
    finally { setBusy('') }
  }

  async function publish() {
    if (!releaseVersion.trim()) return
    setBusy('publish'); setError(''); setMessage('')
    try {
      await persistDraft()
      const published = await publishResource(resourceId, releaseVersion.trim())
      setVersions((current) => [published, ...current])
      setReleaseVersion(''); setIsPublishOpen(false); setMessage(t('lorebookEditor.published'))
    } catch { setError(t('lorebookEditor.publishFailed')) }
    finally { setBusy('') }
  }

  async function exportDraft() {
    setBusy('export'); setError('')
    try {
      await persistDraft()
      const link = window.document.createElement('a')
      link.href = draftDownloadUrl(resourceId); link.download = ''
      window.document.body.appendChild(link); link.click(); link.remove()
    } catch { setError(t('lorebookEditor.saveFailed')) }
    finally { setBusy('') }
  }

  async function importFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy('import'); setError('')
    try { await importLorebook(resourceId, file); window.location.reload() }
    catch { setError(t('lorebookEditor.importFailed')); setBusy(''); event.target.value = '' }
  }

  async function uploadCover(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy('cover'); setError('')
    try {
      const image = await uploadCharacterCover(resourceId, file)
      setCoverImageId(image.id); setAvailableImages((current) => [image, ...current])
      setIsCoverPickerOpen(false)
    } catch { setError(t('editor.imageUploadFailed')) }
    finally { setBusy(''); event.target.value = '' }
  }

  async function selectCover(image) {
    try {
      const updated = await selectCharacterCover(resourceId, image.id)
      setResource(updated); setCoverImageId(image.id); setIsCoverPickerOpen(false)
    } catch { setError(t('editor.imageSelectionFailed')) }
  }

  async function changeVisibility(versionId, visibility) {
    try {
      const updated = await updateVersionVisibility(versionId, visibility)
      setVersions((current) => current.map((version) => version.id === versionId ? updated : version))
    } catch { setError(t('editor.visibilityUpdateFailed')) }
  }

  async function removeResource() {
    if (!window.confirm(t('editor.deleteConfirm'))) return
    try { await deleteResource(resourceId, resource.resourceType); navigate('/resources/mine', { replace: true }) }
    catch { setError(t('editor.deleteFailed')) }
  }

  return (
    <section className="character-editor-page">
      <form className="character-editor" onSubmit={save}>
        <div className="editor-toolbar">
          <div><span className="eyebrow">{t('lorebookEditor.draft')}</span><h1>{resource.metadata.name}</h1></div>
          <div className="editor-actions">
            <button className="danger-button" type="button" onClick={removeResource}>{t('editor.delete')}</button>
            <button type="button" onClick={() => setIsPublishOpen(true)}>{t('editor.publish')}</button>
            <button type="button" disabled={busy === 'import'} onClick={() => importInput.current?.click()}>
              {busy === 'import' ? t('editor.importing') : t('editor.upload')}
            </button>
            <button type="button" disabled={busy === 'export'} onClick={exportDraft}>
              {busy === 'export' ? t('editor.exporting') : t('editor.export')}
            </button>
            <button className="save-button" type="submit" disabled={busy === 'save'}>{t('editor.save')}</button>
            <input ref={importInput} className="visually-hidden" type="file"
              accept=".json,.png,application/json,image/png" onChange={importFile} />
          </div>
        </div>
        {error && <p className="editor-message error" role="alert">{error}</p>}
        {message && <p className="editor-message success" role="status">{message}</p>}

        <section className="resource-metadata-editor">
          <div className="section-heading"><div><h2>{t('editor.resourceMetadata')}</h2>
            <p>{t('lorebookEditor.resourceHelp')}</p></div></div>
          <div className="editor-field-grid">
            <label>{t('resource.name')}<input required maxLength={200} value={resourceFields.name}
              onChange={(event) => setResourceFields((current) => ({ ...current, name: event.target.value }))} /></label>
            <label>{t('resource.visibility')}<select value={resourceFields.visibility}
              onChange={(event) => setResourceFields((current) => ({ ...current, visibility: event.target.value }))}>
              {['private', 'authenticated', 'public'].map((visibility) => <option key={visibility} value={visibility}>
                {t(`resource.visibilities.${visibility}`)}</option>)}
            </select></label>
            <label className="wide-field">{t('resource.description')}<textarea rows={4}
              value={resourceFields.description} onChange={(event) => setResourceFields((current) => ({
                ...current, description: event.target.value,
              }))} /></label>
            <div className="wide-field"><label htmlFor="lorebook-tags">{t('resource.tags')}</label>
              <TagEditor id="lorebook-tags" value={resourceFields.tags}
                onChange={(tags) => setResourceFields((current) => ({ ...current, tags }))} /></div>
          </div>
        </section>

        <div className="editor-summary">
          <button className="character-image-picker" type="button" onClick={() => setIsCoverPickerOpen(true)}>
            {coverImageId ? <ResourceImage imageResourceId={coverImageId} /> : <>
              <span aria-hidden="true">＋</span><strong>{t('lorebookEditor.addCover')}</strong>
              <small>{t('lorebookEditor.coverHelp')}</small></>}
          </button>
          <div className="card-metadata-fields">
            <h2>{t('lorebookEditor.settings')}</h2>
            <div className="editor-field-grid">
              <label>{t('editor.scanDepth')}<input type="number" value={book.scan_depth}
                onChange={(event) => setBook((current) => ({ ...current, scan_depth: event.target.value }))} /></label>
              <label>{t('editor.tokenBudget')}<input type="number" value={book.token_budget}
                onChange={(event) => setBook((current) => ({ ...current, token_budget: event.target.value }))} /></label>
              <label className="checkbox-field"><input type="checkbox" checked={book.recursive_scanning}
                onChange={(event) => setBook((current) => ({ ...current, recursive_scanning: event.target.checked }))} />
                {t('editor.recursiveScanning')}</label>
            </div>
          </div>
        </div>

        <section className="embedded-lorebook">
          <div className="section-heading"><div><h2>{t('lorebookEditor.entries')}</h2>
            <p>{t('lorebookEditor.entriesHelp')}</p></div>
            <button className="add-list-button" type="button"
              onClick={() => setEntries((current) => [...current, newEntry(current.length)])}>
              <span aria-hidden="true">＋</span>{t('editor.addLoreEntry')}
            </button></div>
          <div className="lore-entry-list">{entries.map((entry, index) => (
            <article className="lore-entry" key={entry.localId}>
              <div className="lore-entry-heading"><h3>{entry.name || t('editor.loreEntry', { number: index + 1 })}</h3>
                <button type="button" onClick={() => setEntries((current) => current.filter((item) => item.localId !== entry.localId))}>{t('editor.remove')}</button></div>
              <div className="editor-field-grid">
                <label>{t('editor.entryName')}<input value={entry.name}
                  onChange={(event) => updateEntry(entry.localId, 'name', event.target.value)} /></label>
                <label>{t('editor.keywords')}<input value={entry.keys}
                  onChange={(event) => updateEntry(entry.localId, 'keys', event.target.value)} /></label>
                <label>{t('lorebookEditor.secondaryKeys')}<input value={entry.secondary_keys}
                  onChange={(event) => updateEntry(entry.localId, 'secondary_keys', event.target.value)} /></label>
                <label>{t('editor.insertionOrder')}<input type="number" value={entry.insertion_order}
                  onChange={(event) => updateEntry(entry.localId, 'insertion_order', event.target.value)} /></label>
                <label>{t('lorebookEditor.priority')}<input type="number" value={entry.priority}
                  onChange={(event) => updateEntry(entry.localId, 'priority', event.target.value)} /></label>
                <label>{t('lorebookEditor.position')}<select value={entry.position}
                  onChange={(event) => updateEntry(entry.localId, 'position', event.target.value)}>
                  <option value="">{t('lorebookEditor.unspecified')}</option>
                  <option value="before_char">{t('lorebookEditor.beforeCharacter')}</option>
                  <option value="after_char">{t('lorebookEditor.afterCharacter')}</option>
                </select></label>
              </div>
              <label>{t('editor.entryContent')}<textarea rows={7} value={entry.content} required
                onChange={(event) => updateEntry(entry.localId, 'content', event.target.value)} /></label>
              <label>{t('lorebookEditor.comment')}<input value={entry.comment}
                onChange={(event) => updateEntry(entry.localId, 'comment', event.target.value)} /></label>
              <div className="lore-entry-options">
                {[
                  ['enabled', 'enabled'], ['constant', 'constant'], ['use_regex', 'useRegex'],
                  ['selective', 'selective'], ['case_sensitive', 'caseSensitive'],
                ].map(([field, label]) => <label key={field}><input type="checkbox" checked={Boolean(entry[field])}
                  onChange={(event) => updateEntry(entry.localId, field, event.target.checked)} />
                  {t(field === 'selective' || field === 'case_sensitive' ? `lorebookEditor.${label}` : `editor.${label}`)}</label>)}
              </div>
            </article>
          ))}</div>
        </section>

        <section className="release-history"><div className="section-heading"><div>
          <h2>{t('editor.releases')}</h2><p>{t('editor.releasesHelp')}</p></div></div>
          {versions.length === 0 ? <p className="empty-releases">{t('editor.noReleases')}</p> :
            <div className="release-grid">{versions.map((version) => <article className="release-tile" key={version.id}>
              <div className="release-cover">{version.coverImageResourceId
                ? <ResourceImage imageResourceId={version.coverImageResourceId} /> : <span>◇</span>}</div>
              <div><strong>{version.version}</strong><small>{t('editor.releaseNumber', { number: version.versionNumber })}</small></div>
              <select value={version.visibility} onChange={(event) => changeVisibility(version.id, event.target.value)}>
                {['private', 'authenticated', 'public'].map((visibility) => <option key={visibility} value={visibility}>{t(`resource.visibilities.${visibility}`)}</option>)}
              </select>
            </article>)}</div>}
        </section>

        {isPublishOpen && <div className="cover-picker-backdrop" role="presentation">
          <section className="publish-dialog" role="dialog" aria-modal="true">
            <div className="cover-picker-heading"><div><h2>{t('lorebookEditor.publishTitle')}</h2>
              <p>{t('editor.publishHelp')}</p></div><button type="button" onClick={() => setIsPublishOpen(false)}>×</button></div>
            <label>{t('editor.releaseVersion')}<input autoFocus value={releaseVersion} placeholder="v1.0.0"
              onChange={(event) => setReleaseVersion(event.target.value)} /></label>
            <button className="save-button" type="button" disabled={!releaseVersion.trim() || busy === 'publish'} onClick={publish}>{t('editor.publish')}</button>
          </section>
        </div>}

        {isCoverPickerOpen && <div className="cover-picker-backdrop" role="presentation">
          <section className="cover-picker-dialog" role="dialog" aria-modal="true">
            <div className="cover-picker-heading"><div><h2>{t('editor.chooseCover')}</h2>
              <p>{t('lorebookEditor.coverHelp')}</p></div><button type="button" onClick={() => setIsCoverPickerOpen(false)}>×</button></div>
            <button className="cover-upload-button" type="button" onClick={() => imageInput.current?.click()}>{t('editor.uploadNewImage')}</button>
            <input ref={imageInput} className="visually-hidden" type="file" accept="image/*" onChange={uploadCover} />
            <div className="existing-image-grid">{availableImages.map((image) => <button key={image.id} type="button" onClick={() => selectCover(image)}>
              <ResourceImage imageResourceId={image.id} /><span>{image.metadata.name}</span></button>)}</div>
          </section>
        </div>}
      </form>
    </section>
  )
}
