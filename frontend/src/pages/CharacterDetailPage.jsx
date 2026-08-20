import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  createSignedDownloadUrl, forkResourceVersion, getResource, getResourceVersionData, listResourceVersions,
  versionCoverUrl, versionDownloadUrl,
} from '../api/resources.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { ResourceMetrics } from '../components/ResourceMetrics.jsx'
import { ResourceAuthors } from '../components/ResourceAuthors.jsx'
import { ReleaseDiff } from '../components/ReleaseDiff.jsx'
import { useAuth } from '../auth/useAuth.js'
import { copyText } from '../utils/clipboard.js'


function TextField({ label, value }) {
  if (value === undefined || value === null || value === '') return null
  return <section className="detail-field"><h3>{label}</h3><p>{value}</p></section>
}


function TextList({ label, values }) {
  if (!values?.length) return null
  return (
    <section className="detail-field"><h3>{label}</h3>
      <div className="detail-list">{values.map((value, index) => <p key={index}>{value}</p>)}</div>
    </section>
  )
}


export function CharacterDetailPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const [resource, setResource] = useState(null)
  const [versions, setVersions] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [releaseDocument, setReleaseDocument] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [isForking, setIsForking] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)])
      .then(([loadedResource, loadedVersions]) => {
        if (!active) return
        if (loadedResource.resourceType !== 'sillytavern/character' || !loadedVersions.length) {
          throw new Error('Published character not found')
        }
        setResource(loadedResource)
        setVersions(loadedVersions)
        setSelectedId(loadedVersions[0]?.id ?? '')
      })
      .catch(() => { if (active) { setError(t('details.loadFailed')); setIsLoading(false) } })
    return () => { active = false }
  }, [resourceId, t])

  useEffect(() => {
    if (!selectedId) return undefined
    let active = true
    getResourceVersionData(selectedId)
      .then((loaded) => { if (active) setReleaseDocument(loaded) })
      .catch(() => { if (active) setError(t('details.loadFailed')) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [selectedId, t])

  const version = versions.find((item) => item.id === selectedId)
  const data = releaseDocument?.data
  useEffect(() => {
    if (!resource) return undefined
    document.title = `${resource.metadata.name} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [resource, t])

  if (error) return <div className="page-loading error" role="alert">{error}</div>
  if (isLoading || !resource || !data || !version) {
    return <div className="page-loading" role="status">{t('details.loading')}</div>
  }
  async function copyDownloadLink() {
    setError('')
    try {
      const result = await createSignedDownloadUrl(selectedId)
      await copyText(result.url)
      setActionMessage(t('details.linkCopied', { seconds: result.expiresIn }))
    } catch {
      setError(t('details.copyFailed'))
    }
  }

  async function forkVersion() {
    if (!user) {
      navigate('/login', { state: { from: location.pathname } })
      return
    }
    setError('')
    setIsForking(true)
    try {
      const fork = await forkResourceVersion(selectedId)
      navigate(`/resources/${fork.id}/edit`, { state: { resource: fork } })
    } catch {
      setError(t('details.forkFailed'))
      setIsForking(false)
    }
  }

  const book = data.character_book
  return (
    <article className="character-editor-page character-detail-page">
      <div className="character-editor">
        <header className="editor-toolbar">
          <div><span className="eyebrow">{t('details.publishedCharacter')}</span>
            <h1>{version.metadata.name}</h1></div>
          <div className="detail-version-actions">
            <select value={selectedId} aria-label={t('details.selectVersion')}
              onChange={(event) => {
                setReleaseDocument(null)
                setSelectedId(event.target.value)
              }}>
              {versions.map((item) => <option key={item.id} value={item.id}>
                {item.version} · {new Date(item.publishedAt).toLocaleDateString()}
              </option>)}
            </select>
            <a className="save-button" href={versionDownloadUrl(selectedId)} download>
              {t('details.download')}
            </a>
            <button type="button" onClick={copyDownloadLink}>{t('details.copyLink')}</button>
            <button type="button" disabled={isForking} onClick={forkVersion}>
              {isForking ? t('details.forking') : t('details.fork')}
            </button>
          </div>
        </header>
        {actionMessage && <p className="editor-message success" role="status">{actionMessage}</p>}
        <section className="resource-metadata-editor detail-metadata">
          <h2>{t('editor.resourceMetadata')}</h2>
          <TextField label={t('resource.description')} value={version.metadata.description} />
          <TextField label={t('resource.language')} value={t(`resource.languages.${version.metadata.language === 'zh-cn' ? 'zhCN' : 'enUK'}`)} />
          {!!version.metadata.tags?.length && <div className="detail-tags">
            {version.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>}
          <ResourceAuthors resource={resource} />
          <ResourceMetrics resource={resource} />
        </section>
        <ReleaseDiff diff={version.contentDiff} />
        <div className="editor-summary">
          <div className="character-image-picker detail-cover">
            {version.coverImageResourceId
              ? <ResourceImage src={versionCoverUrl(version.id)} alt={version.metadata.name} />
              : <span aria-hidden="true">◇</span>}
          </div>
          <div className="card-metadata-fields detail-metadata">
            <h2>{t('editor.cardMetadata')}</h2>
            <TextField label={t('editor.name')} value={data.name} />
            <TextField label={t('editor.version')} value={data.character_version} />
            <TextField label={t('editor.nickname')} value={data.nickname} />
            <TextField label={t('details.creator')} value={data.creator} />
          </div>
        </div>
        <section className="editor-content-fields detail-content">
          <h2>{t('editor.characterContent')}</h2>
          {['personality', 'scenario', 'first_mes', 'mes_example', 'creator_notes',
            'system_prompt', 'post_history_instructions'].map((field) => (
              <TextField key={field} label={t(`editor.fields.${field}`)} value={data[field]} />
          ))}
          <TextList label={t('editor.alternateGreetings')} values={data.alternate_greetings} />
          <TextList label={t('editor.groupGreetings')} values={data.group_only_greetings} />
        </section>
        {book && (book.name || book.description || book.entries?.length > 0) && (
          <section className="embedded-lorebook detail-content">
            <h2>{t('editor.lorebook')}</h2>
            <TextField label={t('editor.lorebookName')} value={book.name} />
            <TextField label={t('resource.description')} value={book.description} />
            {book.entries?.map((entry, index) => <article className="lore-entry" key={index}>
              <h3>{entry.name || t('editor.loreEntry', { number: index + 1 })}</h3>
              <TextField label={t('editor.keywords')} value={entry.keys?.join(', ')} />
              <TextField label={t('editor.entryContent')} value={entry.content} />
            </article>)}
          </section>
        )}
        {!!version.linkedLorebooks?.length && <section className="linked-lorebooks detail-content">
          <h2>{t('editor.linkedLorebooks')}</h2><p>{t('details.linkedLorebooksHelp')}</p>
          <div className="linked-lorebook-links">{version.linkedLorebooks.map((lorebook) =>
            <a key={lorebook.versionId} href={`/lorebooks/${lorebook.resourceId}?version=${encodeURIComponent(lorebook.versionId)}`} target="_blank" rel="noopener noreferrer">
              <strong>{lorebook.name || t('editor.linkedLorebooks')}</strong>
              <small>{t('editor.byAuthor', { author: lorebook.author })}</small>
              <small>{t('editor.releaseOption', { version: lorebook.version || lorebook.versionId })}</small>
            </a>)}</div>
        </section>}
      </div>
    </article>
  )
}
