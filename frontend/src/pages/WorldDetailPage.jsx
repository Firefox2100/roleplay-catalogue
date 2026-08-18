import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { getResource, getResourceVersionData, listResourceVersions, resourceImageUrl, versionDownloadUrl } from '../api/resources.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { useAuth } from '../auth/useAuth.js'

export function WorldDetailPage() {
  const { resourceId } = useParams()
  const { t } = useTranslation()
  const { user } = useAuth()
  const [resource, setResource] = useState(null)
  const [versions, setVersions] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [bundle, setBundle] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)])
      .then(([loaded, releases]) => {
        setResource(loaded); setVersions(releases)
        if (releases[0]) setSelectedId(releases[0].id)
      }).catch(() => setError(t('world.loadFailed')))
  }, [resourceId, t])
  useEffect(() => {
    if (!selectedId) return
    getResourceVersionData(selectedId).then((document) => setBundle(document.data)).catch(() => setError(t('world.loadFailed')))
  }, [selectedId, t])

  if (error) return <div className="catalogue-message error">{error}</div>
  if (!resource) return <div className="page-loading">{t('world.loading')}</div>
  const imageUrl = resourceImageUrl(resource)
  return <section className="character-editor-page"><div className="character-editor">
    <header className="editor-toolbar"><div><span className="eyebrow">{t('world.model')}</span><h1>{resource.metadata.name}</h1></div>
      <div className="detail-version-actions">{versions.length > 0 && <><select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{versions.map((version) => <option key={version.id} value={version.id}>{version.version}</option>)}</select><a className="save-button" href={versionDownloadUrl(selectedId)}>{t('details.download')}</a></>}{user?.id === resource.authorId && <Link className="save-button" to={`/worlds/${resource.id}/edit`}>{t('world.edit')}</Link>}</div>
    </header>
    <section className="editor-summary">{imageUrl ? <ResourceImage className="character-image-picker" src={imageUrl} /> : <div className="character-image-picker"><span>◇</span><strong>{t('world.noCover')}</strong></div>}
      <div className="detail-metadata"><div className="detail-field"><h3>{t('resource.description')}</h3><p>{resource.metadata.description || t('home.noDescription')}</p></div>
        {bundle && <><div className="detail-field"><h3>{t('world.startingTime')}</h3><p>{new Date(bundle.world.starting_time).toLocaleString()}</p></div><div className="detail-field"><h3>{t('world.language')}</h3><p>{t(`resource.languages.${resource.metadata.language === 'zh-cn' ? 'zhCN' : 'enUK'}`)}</p></div></>}
        <div className="detail-tags">{resource.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div>
    </section>
    {bundle && <section className="world-overview"><h2>{t('world.contents')}</h2><div className="world-count-grid">{Object.entries(bundle.sections).map(([name, rows]) => <div key={name}><strong>{rows.length}</strong><span>{t(`world.sections.${name}`)}</span></div>)}</div>
      {Object.entries(bundle.sections).filter(([, rows]) => rows.some((row) => row.name)).map(([name, rows]) => <div className="world-detail-list" key={name}><h3>{t(`world.sections.${name}`)}</h3><div>{rows.filter((row) => row.name).map((row) => <span key={row.id}>{row.name}</span>)}</div></div>)}</section>}
  </div></section>
}
