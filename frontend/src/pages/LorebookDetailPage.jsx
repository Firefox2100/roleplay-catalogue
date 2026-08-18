import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  createSignedDownloadUrl, forkResourceVersion, getResource, getResourceVersionData,
  listResourceVersions, versionCoverUrl, versionDownloadUrl,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { copyText } from '../utils/clipboard.js'


function Value({ label, value }) {
  if (value === null || value === undefined || value === '') return null
  return <section className="detail-field"><h3>{label}</h3><p>{String(value)}</p></section>
}


export function LorebookDetailPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const [resource, setResource] = useState(null)
  const [versions, setVersions] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [releaseDocument, setReleaseDocument] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [isForking, setIsForking] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)])
      .then(([loadedResource, loadedVersions]) => {
        if (!active) return
        if (loadedResource.resourceType !== 'sillytavern/lorebook' || !loadedVersions.length) {
          throw new Error('Published lorebook not found')
        }
        setResource(loadedResource); setVersions(loadedVersions); setSelectedId(loadedVersions[0].id)
      }).catch(() => { if (active) setError(t('details.loadFailed')) })
    return () => { active = false }
  }, [resourceId, t])

  useEffect(() => {
    if (!selectedId) return undefined
    let active = true
    getResourceVersionData(selectedId)
      .then((loaded) => { if (active) setReleaseDocument(loaded) })
      .catch(() => { if (active) setError(t('details.loadFailed')) })
    return () => { active = false }
  }, [selectedId, t])

  const version = versions.find((item) => item.id === selectedId)
  const data = releaseDocument?.data
  if (error) return <div className="page-loading error" role="alert">{error}</div>
  if (!resource || !version || !data) return <div className="page-loading">{t('details.loading')}</div>

  async function copyLink() {
    try {
      const result = await createSignedDownloadUrl(selectedId)
      await copyText(result.url)
      setMessage(t('details.linkCopied', { seconds: result.expiresIn }))
    } catch { setError(t('details.copyFailed')) }
  }

  async function fork() {
    if (!user) { navigate('/login', { state: { from: location.pathname } }); return }
    setIsForking(true)
    try {
      const created = await forkResourceVersion(selectedId)
      navigate(`/lorebooks/${created.id}/edit`, { state: { resource: created } })
    } catch { setError(t('details.forkFailed')); setIsForking(false) }
  }

  return <article className="character-editor-page character-detail-page"><div className="character-editor">
    <header className="editor-toolbar">
      <div><span className="eyebrow">{t('lorebookDetails.published')}</span><h1>{version.metadata.name}</h1></div>
      <div className="detail-version-actions">
        <select value={selectedId} onChange={(event) => {
          setReleaseDocument(null); setSelectedId(event.target.value)
        }}>{versions.map((item) => <option key={item.id} value={item.id}>
          {item.version} · {new Date(item.publishedAt).toLocaleDateString()}
        </option>)}</select>
        <a className="save-button" href={versionDownloadUrl(selectedId)} download>{t('details.download')}</a>
        <button type="button" onClick={copyLink}>{t('details.copyLink')}</button>
        <button type="button" disabled={isForking} onClick={fork}>{isForking ? t('details.forking') : t('details.fork')}</button>
      </div>
    </header>
    {message && <p className="editor-message success">{message}</p>}
    <section className="resource-metadata-editor detail-metadata">
      <h2>{t('editor.resourceMetadata')}</h2>
      <Value label={t('resource.description')} value={version.metadata.description} />
      <Value label={t('resource.language')} value={t(`resource.languages.${version.metadata.language === 'zh-cn' ? 'zhCN' : 'enUK'}`)} />
      <Value label={t('details.author')} value={resource.authorUsername} />
      {!!version.metadata.tags?.length && <div className="detail-tags">{version.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>}
    </section>
    <div className="editor-summary">
      <div className="character-image-picker detail-cover">{version.coverImageResourceId
        ? <ResourceImage src={versionCoverUrl(version.id)} alt={version.metadata.name} /> : <span>◇</span>}</div>
      <div className="card-metadata-fields detail-metadata"><h2>{t('lorebookEditor.settings')}</h2>
        <Value label={t('editor.scanDepth')} value={data.scan_depth} />
        <Value label={t('editor.tokenBudget')} value={data.token_budget} />
        {data.recursive_scanning && <Value label={t('editor.recursiveScanning')} value={t('lorebookDetails.yes')} />}
      </div>
    </div>
    {data.entries?.length > 0 && <section className="embedded-lorebook detail-content">
      <h2>{t('lorebookEditor.entries')}</h2>{data.entries.map((entry, index) => <article className="lore-entry" key={entry.id ?? index}>
        <h3>{entry.name || entry.comment || t('editor.loreEntry', { number: index + 1 })}</h3>
        <Value label={t('editor.keywords')} value={entry.keys?.join(', ')} />
        <Value label={t('lorebookEditor.secondaryKeys')} value={entry.secondary_keys?.join(', ')} />
        <Value label={t('editor.entryContent')} value={entry.content} />
        <Value label={t('lorebookEditor.comment')} value={entry.comment} />
        <div className="detail-tags">
          {entry.enabled && <span>{t('editor.enabled')}</span>}
          {entry.constant && <span>{t('editor.constant')}</span>}
          {entry.use_regex && <span>{t('editor.useRegex')}</span>}
          {entry.selective && <span>{t('lorebookEditor.selective')}</span>}
          {entry.case_sensitive && <span>{t('lorebookEditor.caseSensitive')}</span>}
        </div>
      </article>)}</section>}
  </div></article>
}
