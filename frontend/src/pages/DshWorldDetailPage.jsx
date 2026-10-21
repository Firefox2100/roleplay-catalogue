import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { forkResourceVersion, getResource, getResourceVersionData, listResourceVersions, versionDownloadUrl } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ResourceAuthors } from '../components/ResourceAuthors.jsx'
import { ResourceMetrics } from '../components/ResourceMetrics.jsx'
import { ReleaseDiff } from '../components/ReleaseDiff.jsx'

export function DshWorldDetailPage() {
  const { resourceId } = useParams(); const { t } = useTranslation(); const { user } = useAuth()
  const navigate = useNavigate(); const location = useLocation()
  const [resource, setResource] = useState(null); const [versions, setVersions] = useState([])
  const [selected, setSelected] = useState(''); const [document, setDocument] = useState(null); const [error, setError] = useState('')
  const [isForking, setIsForking] = useState(false)
  useEffect(() => { Promise.all([getResource(resourceId), listResourceVersions(resourceId)]).then(([item, releases]) => { if (item.resourceType !== 'dsh-agentic-roleplay/world' || !releases.length) throw new Error(); setResource(item); setVersions(releases); setSelected(releases[0].id) }).catch(() => setError(t('dshWorld.loadFailed'))) }, [resourceId, t])
  useEffect(() => { if (selected) getResourceVersionData(selected).then(setDocument).catch(() => setError(t('dshWorld.loadFailed'))) }, [selected, t])
  if (error) return <div className="page-loading error" role="alert">{error}</div>
  if (!resource || !document) return <div className="page-loading" role="status">{t('dshWorld.loading')}</div>
  const version = versions.find((item) => item.id === selected); const data = document.data
  async function fork() {
    if (!user) { void navigate('/login', { state: { from: location.pathname } }); return }
    setIsForking(true); setError('')
    try { const created = await forkResourceVersion(selected); void navigate(`/agentic-worlds/${created.id}/edit`, { state: { resource: created } }) }
    catch { setError(t('details.forkFailed')); setIsForking(false) }
  }
  return <section className="character-editor-page"><div className="character-editor"><header className="editor-toolbar"><div><span className="eyebrow">{t('dshWorld.publishedWorld')}</span><h1>{resource.metadata.name}</h1></div><div className="detail-version-actions"><select value={selected} onChange={(event) => { setDocument(null); setSelected(event.target.value) }}>{versions.map((item) => <option key={item.id} value={item.id}>{item.version}</option>)}</select><a className="save-button" href={versionDownloadUrl(selected)}>{t('details.download')}</a><button type="button" disabled={isForking} onClick={fork}>{isForking ? t('details.forking') : t('details.fork')}</button>{user?.id === resource.authorId && <Link className="save-button" to={`/agentic-worlds/${resource.id}/edit`}>{t('dshWorld.edit')}</Link>}</div></header>
    <section className="resource-metadata-editor detail-metadata"><h2>{t('editor.resourceMetadata')}</h2><p>{resource.metadata.description}</p><div className="detail-tags">{resource.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div><ResourceAuthors resource={resource} /><ResourceMetrics resource={resource} /></section>
    <section className="preset-settings"><h2>{t('dshWorld.package')}</h2><p>{t('dshWorld.installHelp')}</p><div className="world-count-grid"><div><strong>{data.worldName}</strong><span>{t('dshWorld.worldName')}</span></div><div><strong>{data.files.length}</strong><span>{t('dshWorld.files')}</span></div><div><strong>{(data.byteSize / 1048576).toFixed(1)} MB</strong><span>{t('dshWorld.zipSize')}</span></div><div><strong>{data.worldVersion || '—'}</strong><span>{t('dshWorld.worldVersion')}</span></div><div><strong>{data.folderName}</strong><span>{t('dshWorld.folderName')}</span></div><div><strong>{data.authorName || '—'}</strong><span>{t('dshWorld.packageAuthor')}</span></div></div></section>
    <ReleaseDiff diff={version?.contentDiff} />
  </div></section>
}
