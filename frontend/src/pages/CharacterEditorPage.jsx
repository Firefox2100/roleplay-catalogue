import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import {
  getResource, getResourceData, imageContentUrl, importCharacterCard, listResources, saveResourceData,
  selectCharacterCover, updateResource, uploadCharacterCover,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { TagEditor } from '../components/TagEditor.jsx'

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
  const { user, isLoading: isAuthLoading } = useAuth()
  const imageInput = useRef(null)
  const cardInput = useRef(null)
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [resourceFields, setResourceFields] = useState({ name: '', description: '', tags: [] })
  const [card, setCard] = useState(EMPTY_CARD)
  const [book, setBook] = useState(EMPTY_BOOK)
  const [loreEntries, setLoreEntries] = useState([])
  const [imagePreview, setImagePreview] = useState('')
  const [coverImageId, setCoverImageId] = useState(resource?.coverImageResourceId ?? '')
  const [availableImages, setAvailableImages] = useState([])
  const [isCoverPickerOpen, setIsCoverPickerOpen] = useState(false)
  const [isUploadingImage, setIsUploadingImage] = useState(false)
  const [isImportingCard, setIsImportingCard] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveState, setSaveState] = useState('')
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
    ]).then(([loadedResource, draft]) => {
      if (!active) return
      if (loadedResource.resourceType !== 'sillytavern/character') {
        setError(t('editor.wrongResourceType'))
        return
      }
      setResource(loadedResource)
      setCoverImageId(loadedResource.coverImageResourceId ?? '')
      setResourceFields({
        name: loadedResource.metadata.name,
        description: loadedResource.metadata.description,
        tags: loadedResource.metadata.tags ?? [],
      })
      if (draft) {
        const data = draft.data
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
        }
      } else {
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
  }, [resource, resourceId, t, user])

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ resourceType: 'core/image', author: user.username, limit: 100 })
      .then((images) => { if (active) setAvailableImages(images) })
      .catch(() => {})
    return () => { active = false }
  }, [user])

  useEffect(() => {
    document.title = `${resource?.metadata.name ?? t('editor.title')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [resource, t])

  if (!isAuthLoading && !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (isAuthLoading || isLoading) {
    return <div className="page-loading" role="status">{t('editor.loading')}</div>
  }

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

  async function saveDraft(event) {
    event.preventDefault()
    setError('')
    setSaveState('')
    setIsSaving(true)
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
    try {
      const updatedResource = await updateResource(resourceId, resourceFields)
      setResource(updatedResource)
      await saveResourceData(resourceId, {
        ...card,
        creator: '',
        description: '',
        tags: [],
        nickname: card.nickname || null,
        character_book: characterBook,
      })
      setSaveState(t('editor.saved'))
    } catch (requestError) {
      setError(requestError.status === 422 ? t('editor.validationFailed') : t('editor.saveFailed'))
    } finally {
      setIsSaving(false)
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
      setImagePreview(imageContentUrl(image.id))
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
      setImagePreview(imageContentUrl(image.id))
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
      await importCharacterCard(resourceId, file)
      window.location.reload()
    } catch {
      setError(t('editor.cardImportFailed'))
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
            <button type="button" disabled title={t('editor.notAvailable')}>{t('editor.publish')}</button>
            <button type="button" disabled={isImportingCard}
              onClick={() => cardInput.current?.click()}>
              {isImportingCard ? t('editor.importing') : t('editor.upload')}
            </button>
            <button type="button" disabled title={t('editor.notAvailable')}>{t('editor.export')}</button>
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
        </section>

        <div className="editor-summary">
          <button className="character-image-picker" type="button"
            onClick={() => setIsCoverPickerOpen(true)}>
            {coverImageId ? <img src={imagePreview || imageContentUrl(coverImageId)} alt="" /> : (
              <><span aria-hidden="true">＋</span><strong>{t('editor.addImage')}</strong><small>{t('editor.imageHelp')}</small></>
            )}
          </button>

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
                      <img src={imageContentUrl(image.id)} alt="" />
                      <span>{image.metadata.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </form>
    </section>
  )
}
