import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  clearCharacterCover, deleteResource, draftDownloadUrl, getResource, getResourceData, importCharacterCard, listResources, saveResourceData,
  listResourceVersions, publishResource, selectCharacterCover, updateResource,
  updateVersionVisibility, uploadCharacterCover,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { TagEditor } from '../components/TagEditor.jsx'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { CoAuthorEditor } from '../components/CoAuthorEditor.jsx'
import { ConflictResolutionModal } from '../components/ConflictResolutionModal.jsx'
import { useConflictAwareSave } from '../hooks/useConflictAwareSave.js'
import { resourceToMetadataPayload } from '../utils/resourceMetadataPayload.js'

function toCharacterMetadataPayload(resource) {
  return { ...resourceToMetadataPayload(resource), linkedLorebooks: resource.linkedLorebooks ?? [] }
}

const EMPTY_CARD = {
  name: '', creator: '', character_version: '', nickname: '', tags: '',
  description: '', personality: '', scenario: '', first_mes: '', mes_example: '',
  creator_notes: '', system_prompt: '', post_history_instructions: '',
  alternate_greetings: [], group_only_greetings: [], extensions: {},
}

const EMPTY_BOOK = {
  name: '', description: '', scan_depth: '', token_budget: '', recursive_scanning: false,
}

function newLoreEntry(index = 0) {
  return {
    localId: crypto.randomUUID(), name: '', keys: '', content: '', enabled: true,
    insertion_order: index, use_regex: false, constant: false, comment: '',
  }
}

function RepeatableTextList({ label, values, onChange, placeholder }) {
  const { t } = useTranslation()
  return (
    <fieldset className="repeatable-field">
      <legend>{label}</legend>
      {values.map((value, index) => (
        <div className="repeatable-row" key={index}>
          <textarea value={value} rows={3} placeholder={placeholder}
            onChange={(event) => onChange(values.map((item, itemIndex) => (
              itemIndex === index ? event.target.value : item
            )))} />
          <button type="button" aria-label={t('editor.removeEntry')}
            onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>×</button>
        </div>
      ))}
      <button className="add-list-button" type="button" onClick={() => onChange([...values, ''])}>
        <span aria-hidden="true">＋</span>{t('editor.addEntry')}
      </button>
    </fieldset>
  )
}

export function CharacterEditorPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isLoading: isAuthLoading } = useAuth()
  const imageInput = useRef(null)
  const cardInput = useRef(null)
  const [initialResource] = useState(() => location.state?.resource ?? null)
  const [resource, setResource] = useState(initialResource)
  const [resourceFields, setResourceFields] = useState({ name: '', description: '', language: 'en-uk', visibility: 'private', tags: [] })
  const [card, setCard] = useState(EMPTY_CARD)
  const [book, setBook] = useState(EMPTY_BOOK)
  const [loreEntries, setLoreEntries] = useState([])
  const [coverImageId, setCoverImageId] = useState(resource?.coverImageResourceId ?? '')
  const [availableImages, setAvailableImages] = useState([])
  const [availableLorebooks, setAvailableLorebooks] = useState([])
  const [linkedLorebooks, setLinkedLorebooks] = useState([])
  const [isCoverPickerOpen, setIsCoverPickerOpen] = useState(false)
  const [isUploadingImage, setIsUploadingImage] = useState(false)
  const [isImportingCard, setIsImportingCard] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [versions, setVersions] = useState([])
  const [isPublishOpen, setIsPublishOpen] = useState(false)
  const [releaseVersion, setReleaseVersion] = useState('')
  const [isPublishing, setIsPublishing] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [saveState, setSaveState] = useState('')
  const [error, setError] = useState('')
  const [dataRevision, setDataRevision] = useState(null)
  const [dataBase, setDataBase] = useState({})

  function applyDraftData(data) {
    setCard({
      ...EMPTY_CARD, ...data,
      tags: data.tags?.join(', ') ?? '',
      nickname: data.nickname ?? '',
      alternate_greetings: data.alternate_greetings ?? [],
      group_only_greetings: data.group_only_greetings ?? [],
    })
    if (data.character_book) {
      setBook({
        name: data.character_book.name ?? '',
        description: data.character_book.description ?? '',
        scan_depth: data.character_book.scan_depth ?? '',
        token_budget: data.character_book.token_budget ?? '',
        recursive_scanning: data.character_book.recursive_scanning ?? false,
      })
      setLoreEntries(data.character_book.entries.map((entry, index) => ({
        ...newLoreEntry(index), ...entry,
        name: entry.name ?? '',
        comment: entry.comment ?? '',
        keys: entry.keys.join(', '),
      })))
    } else {
      setBook({ ...EMPTY_BOOK })
      setLoreEntries([])
    }
  }

  useEffect(() => {
    if (!user) return undefined
    let active = true
    const resourceRequest = initialResource
      ? Promise.resolve(initialResource)
      : getResource(resourceId)
    Promise.all([
      resourceRequest,
      getResourceData(resourceId).catch((requestError) => (
        requestError.status === 404 ? null : Promise.reject(requestError)
      )),
    ]).then(([loadedResource, draft]) => {
      if (!active) return
      if (loadedResource.resourceType !== 'sillytavern/character') {
        setError(t('editor.wrongResourceType'))
        return
      }
      setResource(loadedResource)
      setCoverImageId(loadedResource.coverImageResourceId ?? '')
      setLinkedLorebooks(loadedResource.linkedLorebooks ?? (loadedResource.linkedLorebookResourceIds ?? []).map((resourceId) => ({ resourceId, versionId: null })))
      setResourceFields({
        name: loadedResource.metadata.name,
        description: loadedResource.metadata.description,
        language: loadedResource.metadata.language ?? 'en-uk',
        visibility: loadedResource.metadata.visibility,
        tags: loadedResource.metadata.tags ?? [],
      })
      if (draft) {
        setDataRevision(draft.revision)
        setDataBase(draft.data)
        applyDraftData(draft.data)
      } else {
        setDataRevision(null)
        setDataBase({})
        setCard({ ...EMPTY_CARD })
        setBook({ ...EMPTY_BOOK })
        setLoreEntries([])
      }
    }).catch(() => {
      if (active) setError(t('editor.loadFailed'))
    }).finally(() => {
      if (active) setIsLoading(false)
    })
    return () => { active = false }
  }, [initialResource, resourceId, t, user])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ resourceType: 'core/image', author: user.username, limit: 100 })
      .then((page) => { if (active) setAvailableImages(page.items) })
      .catch(() => {})
    return () => { active = false }
  }, [user])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ resourceType: 'sillytavern/lorebook', limit: 100 })
      .then(async (page) => Promise.all(page.items.map(async (item) => ({
        ...item, versions: await listResourceVersions(item.id).catch(() => []),
      }))))
      .then((items) => { if (active) setAvailableLorebooks(items) })
      .catch(() => {})
    return () => { active = false }
  }, [user])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResourceVersions(resourceId)
      .then((loadedVersions) => { if (active) setVersions(loadedVersions) })
      .catch(() => {})
    return () => { active = false }
  }, [resourceId, user])

  useEffect(() => {
    document.title = `${resource?.metadata.name ?? t('editor.title')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [resource, t])

  const metadataSave = useConflictAwareSave({
    apiSave: (payload, revision) => updateResource(resourceId, payload, revision),
    extractComparable: toCharacterMetadataPayload,
    extractRevision: (full) => full.revision,
    onSaved: (updatedResource) => {
      setResource(updatedResource)
      setResourceFields({
        name: updatedResource.metadata.name,
        description: updatedResource.metadata.description,
        language: updatedResource.metadata.language ?? 'en-uk',
        visibility: updatedResource.metadata.visibility,
        tags: updatedResource.metadata.tags ?? [],
      })
      setLinkedLorebooks(updatedResource.linkedLorebooks ?? [])
    },
  })

  const dataSave = useConflictAwareSave({
    apiSave: (payload, revision) => saveResourceData(resourceId, payload, revision),
    extractComparable: (full) => full.data,
    extractRevision: (full) => full.revision,
    onSaved: (savedDocument) => {
      setDataRevision(savedDocument.revision)
      setDataBase(savedDocument.data)
      applyDraftData(savedDocument.data)
    },
  })

  if (!isAuthLoading && !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (isAuthLoading || isLoading) {
    return <div className="page-loading" role="status">{t('editor.loading')}</div>
  }

  const isOwner = user.id === resource.authorId

  function updateCard(field, value) {
    setCard((current) => ({ ...current, [field]: value }))
    setSaveState('')
  }

  function updateBook(field, value) {
    setBook((current) => ({ ...current, [field]: value }))
    setSaveState('')
  }

  function updateLoreEntry(localId, field, value) {
    setLoreEntries((entries) => entries.map((entry) => (
      entry.localId === localId ? { ...entry, [field]: value } : entry
    )))
    setSaveState('')
  }

  function optionalNumber(value) {
    return value === '' || value === null ? null : Number(value)
  }

  async function removeResource() {
    if (!window.confirm(t('editor.deleteConfirm'))) return
    try { await deleteResource(resourceId, resource.resourceType); navigate('/resources/mine', { replace: true }) }
    catch { setError(t('editor.deleteFailed')) }
  }

  function makeDraftData() {
    const hasBook = loreEntries.length > 0 || book.name || book.description
    const characterBook = hasBook ? {
      name: book.name || null,
      description: book.description || null,
      scan_depth: optionalNumber(book.scan_depth),
      token_budget: optionalNumber(book.token_budget),
      recursive_scanning: book.recursive_scanning,
      extensions: {},
      entries: loreEntries.map((entry) => {
        const savedEntry = {
          ...entry,
          keys: entry.keys.split(',').map((key) => key.trim()).filter(Boolean),
          insertion_order: Number(entry.insertion_order),
          extensions: {},
        }
        delete savedEntry.localId
        return savedEntry
      }),
    } : null
    return {
      ...card,
      description: '',
      tags: [],
      nickname: card.nickname || null,
      character_book: characterBook,
    }
  }

  // Returns false (instead of throwing) when a save was blocked by a merge conflict: the
  // conflict modal is now open, and the caller should stop without treating this as success.
  async function persistDraft() {
    const savedResource = await metadataSave.attempt(
      { ...resourceFields, linkedLorebooks }, toCharacterMetadataPayload(resource), resource.revision,
    )
    if (!savedResource) return false

    const savedData = await dataSave.attempt(makeDraftData(), dataBase, dataRevision)
    if (!savedData) return false

    return true
  }

  async function saveDraft(event) {
    event.preventDefault()
    setError('')
    setSaveState('')
    setIsSaving(true)
    try {
      if (await persistDraft()) setSaveState(t('editor.saved'))
    } catch (requestError) {
      setError(requestError.status === 422 ? t('editor.validationFailed') : t('editor.saveFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  async function retryMetadataConflict(resolved) {
    setError('')
    try {
      const savedResource = await metadataSave.retry(resolved)
      if (!savedResource) return
      const savedData = await dataSave.attempt(makeDraftData(), dataBase, dataRevision)
      if (savedData) setSaveState(t('editor.saved'))
    } catch {
      setError(t('editor.conflictRetryFailed'))
    }
  }

  async function retryDataConflict(resolved) {
    setError('')
    try {
      if (await dataSave.retry(resolved)) setSaveState(t('editor.saved'))
    } catch {
      setError(t('editor.conflictRetryFailed'))
    }
  }

  async function publishCurrentDraft() {
    if (!releaseVersion.trim()) return
    if (linkedLorebooks.some((link) => !link.versionId)) {
      setError(t('editor.selectLorebookReleases'))
      return
    }
    setError('')
    setSaveState('')
    setIsPublishing(true)
    try {
      if (!await persistDraft()) return
      const published = await publishResource(resourceId, releaseVersion.trim())
      setVersions((current) => [published, ...current])
      setIsPublishOpen(false)
      setReleaseVersion('')
      setSaveState(t('editor.published'))
    } catch (requestError) {
      setError(requestError.status === 422 ? t('editor.validationFailed') : t('editor.publishFailed'))
    } finally {
      setIsPublishing(false)
    }
  }

  async function changeVersionVisibility(versionId, visibility) {
    try {
      const updated = await updateVersionVisibility(versionId, visibility)
      setVersions((current) => current.map((version) => (
        version.id === versionId ? updated : version
      )))
    } catch {
      setError(t('editor.visibilityUpdateFailed'))
    }
  }

  async function exportDraft() {
    setError('')
    setSaveState('')
    setIsExporting(true)
    try {
      if (!await persistDraft()) return
      const link = window.document.createElement('a')
      link.href = draftDownloadUrl(resourceId)
      link.download = ''
      window.document.body.appendChild(link)
      link.click()
      link.remove()
      setSaveState(t('editor.saved'))
    } catch (requestError) {
      setError(requestError.status === 422 ? t('editor.validationFailed') : t('editor.saveFailed'))
    } finally {
      setIsExporting(false)
    }
  }

  async function uploadCoverImage(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setIsUploadingImage(true)
    setError('')
    try {
      const image = await uploadCharacterCover(resourceId, file)
      setCoverImageId(image.id)
      setAvailableImages((images) => [image, ...images])
      setIsCoverPickerOpen(false)
    } catch {
      setError(t('editor.imageUploadFailed'))
    } finally {
      setIsUploadingImage(false)
      event.target.value = ''
    }
  }

  async function chooseExistingCover(image) {
    setError('')
    try {
      const updatedResource = await selectCharacterCover(resourceId, image.id)
      setResource(updatedResource)
      setCoverImageId(image.id)
      setIsCoverPickerOpen(false)
    } catch {
      setError(t('editor.imageSelectionFailed'))
    }
  }

  async function importCard(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setIsImportingCard(true)
    setError('')
    try {
      const imported = await importCharacterCard(resourceId, file)
      const importedResource = imported.resource
      const importedDraft = imported.draft
      setResource(importedResource)
      setCoverImageId(importedResource.coverImageResourceId ?? '')
      setLinkedLorebooks(importedResource.linkedLorebooks ?? [])
      setResourceFields({
        name: importedResource.metadata.name,
        description: importedResource.metadata.description,
        language: importedResource.metadata.language ?? 'en-uk',
        visibility: importedResource.metadata.visibility,
        tags: importedResource.metadata.tags ?? [],
      })
      setDataRevision(importedDraft.revision)
      setDataBase(importedDraft.data)
      applyDraftData(importedDraft.data)
    } catch {
      setError(t('editor.cardImportFailed'))
    } finally {
      setIsImportingCard(false)
      event.target.value = ''
    }
  }

  return (
    <section className="character-editor-page">
      <form className="character-editor" onSubmit={saveDraft}>
        <div className="editor-toolbar">
          <div>
            <span className="eyebrow">{t('editor.draft')}</span>
            <h1>{resource?.metadata.name}</h1>
          </div>
          <div className="editor-actions">
            {isOwner && <button className="danger-button" type="button" onClick={removeResource}>{t('editor.delete')}</button>}
            {isOwner && <button type="button" disabled={isPublishing}
              onClick={() => setIsPublishOpen(true)}>{t('editor.publish')}</button>}
            <button type="button" disabled={isImportingCard}
              onClick={() => cardInput.current?.click()}>
              {isImportingCard ? t('editor.importing') : t('editor.upload')}
            </button>
            <button type="button" disabled={isExporting} onClick={exportDraft}>
              {isExporting ? t('editor.exporting') : t('editor.export')}
            </button>
            <button className="save-button" type="submit" disabled={isSaving}>
              {isSaving ? t('editor.saving') : t('editor.save')}
            </button>
            <input ref={cardInput} className="visually-hidden" type="file"
              accept=".json,.png,application/json,image/png" onChange={importCard} />
          </div>
        </div>

        {error && <p className="editor-message error" role="alert">{error}</p>}
        {saveState && <p className="editor-message success" role="status">{saveState}</p>}

        <section className="resource-metadata-editor">
          <div className="section-heading">
            <div><h2>{t('editor.resourceMetadata')}</h2><p>{t('editor.resourceMetadataHelp')}</p></div>
          </div>
          <div className="editor-field-grid">
            <label>{t('resource.name')}<input value={resourceFields.name} required maxLength={200}
              onChange={(event) => setResourceFields((fields) => ({
                ...fields, name: event.target.value,
              }))} /></label>
            <label>{t('resource.visibility')}<select value={resourceFields.visibility}
              onChange={(event) => setResourceFields((current) => ({ ...current, visibility: event.target.value }))}>
              {['private', 'authenticated', 'public'].map((visibility) => <option key={visibility} value={visibility}>
                {t(`resource.visibilities.${visibility}`)}</option>)}
            </select></label>
            <label>{t('resource.language')}<select value={resourceFields.language}
              onChange={(event) => setResourceFields((current) => ({ ...current, language: event.target.value }))}>
              <option value="en-uk">{t('resource.languages.enUK')}</option><option value="zh-cn">{t('resource.languages.zhCN')}</option>
            </select></label>
            <label className="wide-field">{t('resource.description')}<textarea rows={4}
              value={resourceFields.description} maxLength={10000}
              onChange={(event) => setResourceFields((fields) => ({
                ...fields, description: event.target.value,
              }))} /></label>
            <div className="wide-field resource-tag-field">
              <label htmlFor="editor-resource-tags">{t('resource.tags')}</label>
              <TagEditor id="editor-resource-tags" value={resourceFields.tags}
                onChange={(tags) => setResourceFields((fields) => ({ ...fields, tags }))} />
            </div>
          </div>
          <CoAuthorEditor resourceId={resource.id} authorId={resource.authorId} currentUserId={user.id} />
        </section>

        <div className="editor-summary">
          <div><button className="character-image-picker" type="button"
              onClick={() => setIsCoverPickerOpen(true)}>
              {coverImageId ? <ResourceImage imageResourceId={coverImageId} /> : (
                <><span aria-hidden="true">＋</span><strong>{t('editor.addImage')}</strong><small>{t('editor.imageHelp')}</small></>
              )}
            </button>{coverImageId && <button className="danger-outline" type="button"
              onClick={async () => { try { const updated = await clearCharacterCover(resourceId); setResource(updated); setCoverImageId('') } catch { setError(t('editor.imageSelectionFailed')) } }}>
              {t('editor.clearCover')}</button>}</div>

          <div className="card-metadata-fields">
            <h2>{t('editor.cardMetadata')}</h2>
            <div className="editor-field-grid">
              <label>{t('editor.name')}<input value={card.name} required
                onChange={(event) => updateCard('name', event.target.value)} /></label>
              <label>{t('editor.version')}<input value={card.character_version}
                onChange={(event) => updateCard('character_version', event.target.value)} /></label>
              <label>{t('editor.nickname')}<input value={card.nickname}
                onChange={(event) => updateCard('nickname', event.target.value)} /></label>
            </div>
          </div>
        </div>

        <div className="editor-content-fields">
          <h2>{t('editor.characterContent')}</h2>
          {[['personality', 5], ['scenario', 5], ['first_mes', 6],
            ['mes_example', 7], ['creator_notes', 5], ['system_prompt', 5],
            ['post_history_instructions', 5]].map(([field, rows]) => (
              <label key={field}>{t(`editor.fields.${field}`)}
                <textarea rows={rows} value={card[field]}
                  onChange={(event) => updateCard(field, event.target.value)} />
              </label>
            ))}
          <RepeatableTextList label={t('editor.alternateGreetings')}
            values={card.alternate_greetings}
            onChange={(values) => updateCard('alternate_greetings', values)} />
          <RepeatableTextList label={t('editor.groupGreetings')}
            values={card.group_only_greetings}
            onChange={(values) => updateCard('group_only_greetings', values)} />
        </div>

        <section className="embedded-lorebook">
          <div className="section-heading">
            <div><h2>{t('editor.lorebook')}</h2><p>{t('editor.lorebookHelp')}</p></div>
            <button className="add-list-button" type="button"
              onClick={() => setLoreEntries((entries) => [...entries, newLoreEntry(entries.length)])}>
              <span aria-hidden="true">＋</span>{t('editor.addLoreEntry')}
            </button>
          </div>
          <div className="editor-field-grid lorebook-metadata">
            <label>{t('editor.lorebookName')}<input value={book.name}
              onChange={(event) => updateBook('name', event.target.value)} /></label>
            <label>{t('resource.description')}<input value={book.description}
              onChange={(event) => updateBook('description', event.target.value)} /></label>
            <label>{t('editor.scanDepth')}<input type="number" value={book.scan_depth}
              onChange={(event) => updateBook('scan_depth', event.target.value)} /></label>
            <label>{t('editor.tokenBudget')}<input type="number" value={book.token_budget}
              onChange={(event) => updateBook('token_budget', event.target.value)} /></label>
            <label className="checkbox-field"><input type="checkbox" checked={book.recursive_scanning}
              onChange={(event) => updateBook('recursive_scanning', event.target.checked)} />
              {t('editor.recursiveScanning')}</label>
          </div>
          <div className="lore-entry-list">
            {loreEntries.map((entry, index) => (
              <article className="lore-entry" key={entry.localId}>
                <div className="lore-entry-heading"><h3>{t('editor.loreEntry', { number: index + 1 })}</h3>
                  <button type="button" onClick={() => setLoreEntries((entries) => (
                    entries.filter((item) => item.localId !== entry.localId)
                  ))}>{t('editor.remove')}</button></div>
                <div className="editor-field-grid">
                  <label>{t('editor.entryName')}<input value={entry.name}
                    onChange={(event) => updateLoreEntry(entry.localId, 'name', event.target.value)} /></label>
                  <label>{t('editor.keywords')}<input value={entry.keys} required
                    onChange={(event) => updateLoreEntry(entry.localId, 'keys', event.target.value)} /></label>
                  <label>{t('editor.insertionOrder')}<input type="number" value={entry.insertion_order}
                    onChange={(event) => updateLoreEntry(entry.localId, 'insertion_order', event.target.value)} /></label>
                </div>
                <label>{t('editor.entryContent')}<textarea rows={5} value={entry.content} required
                  onChange={(event) => updateLoreEntry(entry.localId, 'content', event.target.value)} /></label>
                <div className="lore-entry-options">
                  {[['enabled', 'enabled'], ['constant', 'constant'], ['use_regex', 'useRegex']].map(([field, label]) => (
                    <label key={field}><input type="checkbox" checked={entry[field]}
                      onChange={(event) => updateLoreEntry(entry.localId, field, event.target.checked)} />
                      {t(`editor.${label}`)}</label>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="linked-lorebooks">
          <div className="section-heading"><div><h2>{t('editor.linkedLorebooks')}</h2>
            <p>{t('editor.linkedLorebooksHelp')}</p></div></div>
          {availableLorebooks.length ? <div className="linked-lorebook-options">
            {availableLorebooks.map((lorebook) => {
              const link = linkedLorebooks.find((item) => item.resourceId === lorebook.id)
              const value = link ? (link.versionId || 'draft') : ''
              const ownsDraft = lorebook.authorId === user.id && lorebook.draftDataId
              return <label key={lorebook.id}><span><strong>{lorebook.metadata.name}</strong>
                <small>{t('editor.byAuthor', { author: lorebook.authorUsername })}</small>
                {lorebook.metadata.description && <small>{lorebook.metadata.description}</small>}</span>
                <select value={value} onChange={(event) => setLinkedLorebooks((current) => {
                  const others = current.filter((item) => item.resourceId !== lorebook.id)
                  if (!event.target.value) return others
                  return [...others, { resourceId: lorebook.id, versionId: event.target.value === 'draft' ? null : event.target.value }]
                })}><option value="">{t('editor.notLinked')}</option>
                  {ownsDraft && <option value="draft">{t('editor.currentDraft')}</option>}
                  {lorebook.versions.map((version) => <option key={version.id} value={version.id}>{t('editor.releaseOption', { version: version.version })}</option>)}
                </select></label>
            })}
          </div> : <p className="empty-releases">{t('editor.noLorebooks')}</p>}
        </section>

        <section className="release-history">
          <div className="section-heading">
            <div><h2>{t('editor.releases')}</h2><p>{t('editor.releasesHelp')}</p></div>
          </div>
          {versions.length === 0 ? <p className="empty-releases">{t('editor.noReleases')}</p> : (
            <div className="release-grid">
              {versions.map((version) => (
                <article className="release-tile" key={version.id}>
                  <div className="release-cover">
                    {version.coverImageResourceId
                      ? <ResourceImage imageResourceId={version.coverImageResourceId} />
                      : <span aria-hidden="true">◇</span>}
                  </div>
                  <div>
                    <strong>{version.version}</strong>
                    <small>{t('editor.releaseNumber', { number: version.versionNumber })}</small>
                  </div>
                  {isOwner ? (
                    <select value={version.visibility} aria-label={t('resource.visibility')}
                      onChange={(event) => changeVersionVisibility(version.id, event.target.value)}>
                      <option value="private">{t('resource.visibilities.private')}</option>
                      <option value="authenticated">{t('resource.visibilities.authenticated')}</option>
                      <option value="public">{t('resource.visibilities.public')}</option>
                    </select>
                  ) : <small>{t(`resource.visibilities.${version.visibility}`)}</small>}
                </article>
              ))}
            </div>
          )}
        </section>

        {isPublishOpen && (
          <div className="cover-picker-backdrop" role="presentation"
            onMouseDown={() => !isPublishing && setIsPublishOpen(false)}>
            <section className="publish-dialog" role="dialog" aria-modal="true"
              aria-labelledby="publish-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
              <div className="cover-picker-heading">
                <div><h2 id="publish-dialog-title">{t('editor.publishTitle')}</h2>
                  <p>{t('editor.publishHelp')}</p></div>
                <button type="button" disabled={isPublishing}
                  onClick={() => setIsPublishOpen(false)}>×</button>
              </div>
              <label>{t('editor.releaseVersion')}
                <input autoFocus value={releaseVersion} maxLength={100} placeholder="v1.0.0"
                  onChange={(event) => setReleaseVersion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') { event.preventDefault(); publishCurrentDraft() }
                  }} />
              </label>
              <button className="save-button" type="button"
                disabled={isPublishing || !releaseVersion.trim()} onClick={publishCurrentDraft}>
                {isPublishing ? t('editor.publishing') : t('editor.publish')}
              </button>
            </section>
          </div>
        )}

        {isCoverPickerOpen && (
          <div className="cover-picker-backdrop" role="presentation"
            onMouseDown={() => setIsCoverPickerOpen(false)}>
            <section className="cover-picker-dialog" role="dialog" aria-modal="true"
              aria-labelledby="cover-picker-title" onMouseDown={(event) => event.stopPropagation()}>
              <div className="cover-picker-heading">
                <div><h2 id="cover-picker-title">{t('editor.chooseCover')}</h2>
                  <p>{t('editor.chooseCoverHelp')}</p></div>
                <button type="button" onClick={() => setIsCoverPickerOpen(false)}>×</button>
              </div>
              <button className="cover-upload-button" type="button" disabled={isUploadingImage}
                onClick={() => imageInput.current?.click()}>
                {isUploadingImage ? t('editor.uploadingImage') : t('editor.uploadNewImage')}
              </button>
              <input ref={imageInput} className="visually-hidden" type="file" accept="image/*"
                onChange={uploadCoverImage} />
              {availableImages.length > 0 && (
                <div className="existing-image-grid">
                  {availableImages.map((image) => (
                    <button key={image.id} type="button" onClick={() => chooseExistingCover(image)}>
                      <ResourceImage imageResourceId={image.id} />
                      <span>{image.metadata.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </form>
      {metadataSave.conflict && (
        <ConflictResolutionModal
          conflicts={metadataSave.conflict.conflicts}
          merged={metadataSave.conflict.merged}
          isRetrying={metadataSave.isRetrying}
          onApply={retryMetadataConflict}
          onCancel={metadataSave.cancel}
        />
      )}
      {dataSave.conflict && (
        <ConflictResolutionModal
          conflicts={dataSave.conflict.conflicts}
          merged={dataSave.conflict.merged}
          isRetrying={dataSave.isRetrying}
          onApply={retryDataConflict}
          onCancel={dataSave.cancel}
        />
      )}
    </section>
  )
}
