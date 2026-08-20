import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import {
  createSignedDownloadUrl, getResource, imageContentUrl,
  listResourceVersions, versionDownloadUrl,
} from '../api/resources.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { ResourceMetrics } from '../components/ResourceMetrics.jsx'
import { ResourceAuthors } from '../components/ResourceAuthors.jsx'
import { copyText } from '../utils/clipboard.js'


export function ImageDetailPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const [resource, setResource] = useState(null)
  const [version, setVersion] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function copyDownloadLink() {
    setError('')
    try {
      const result = await createSignedDownloadUrl(version.id)
      await copyText(result.url)
      setMessage(t('details.linkCopied', { seconds: result.expiresIn }))
    } catch {
      setError(t('details.copyFailed'))
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)])
      .then(([loadedResource, versions]) => {
        if (!active) return
        if (loadedResource.resourceType !== 'core/image' || !versions.length) {
          throw new Error('Published image not found')
        }
        setResource(loadedResource)
        setVersion(versions[0] ?? null)
      }).catch(() => { if (active) setError(t('details.loadFailed')) })
    return () => { active = false }
  }, [resourceId, t])

  if (error) return <div className="page-loading error" role="alert">{error}</div>
  if (!resource || !version) return <div className="page-loading">{t('details.loading')}</div>
  return (
    <article className="image-editor-page">
      <div className="image-editor-card">
        <header className="image-editor-heading">
          <div><span className="eyebrow">{t('details.publishedImage')}</span>
            <h1>{version.metadata.name}</h1></div>
          <div className="detail-version-actions">
            <a className="save-button" href={versionDownloadUrl(version.id)} download>
              {t('details.download')}
            </a>
            <button type="button" onClick={copyDownloadLink}>{t('details.copyLink')}</button>
          </div>
        </header>
        {message && <p className="editor-message success" role="status">{message}</p>}
        <div className="image-editor-layout">
          <ResourceImage className="image-editor-preview" src={imageContentUrl(resourceId)}
            alt={version.metadata.name} />
          <div className="image-detail-metadata">
            {version.metadata.description && <section><h2>{t('resource.description')}</h2>
              <p>{version.metadata.description}</p></section>}
            <section><h2>{t('resource.language')}</h2><p>{t(`resource.languages.${version.metadata.language === 'zh-cn' ? 'zhCN' : 'enUK'}`)}</p></section>
            <ResourceAuthors resource={resource} />
            <ResourceMetrics resource={resource} />
            {!!version.metadata.tags?.length && <div className="detail-tags">
              {version.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>}
          </div>
        </div>
      </div>
    </article>
  )
}
