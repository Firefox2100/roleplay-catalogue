import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { listResources, resourceImageUrl } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ResourceImage } from '../components/ResourceImage.jsx'

const RESOURCE_TABS = [
  { value: '', label: 'all' },
  { value: 'sillytavern/character', label: 'characters' },
  { value: 'sillytavern/lorebook', label: 'lorebooks' },
  { value: 'core/image', label: 'images' },
  { value: 'world-simulation-engine/world', label: 'worlds' },
]

function PersonalResourceCard({ resource }) {
  const { t } = useTranslation()
  const isCharacter = resource.resourceType === 'sillytavern/character'
  const isLorebook = resource.resourceType === 'sillytavern/lorebook'
  const isImage = resource.resourceType === 'core/image'
  const isWorld = resource.resourceType === 'world-simulation-engine/world'
  const isEditable = isCharacter || isLorebook || isImage || isWorld
  const imageUrl = resourceImageUrl(resource)
  const content = (
    <article className={`catalogue-card ${isEditable ? 'editable' : 'unavailable'}`}>
      {imageUrl ? (
        <ResourceImage className="resource-grid-image" src={imageUrl} />
      ) : (
        <div className="resource-cover-placeholder" aria-label={t('home.imagePlaceholder')}>
          <span aria-hidden="true">◇</span>
        </div>
      )}
      <h2>{resource.metadata.name}</h2>
      {!isEditable && <small className="not-editable-label">{t('myResources.editorComingSoon')}</small>}
      <div className="resource-description-tooltip" role="tooltip">
        {resource.metadata.description || t('home.noDescription')}
      </div>
    </article>
  )

  if (!isEditable) return content
  const editorPath = isImage
    ? `/images/${resource.id}/edit`
    : isLorebook ? `/lorebooks/${resource.id}/edit`
      : isWorld ? `/worlds/${resource.id}/edit` : `/resources/${resource.id}/edit`
  return (
    <Link className="my-resource-link" to={editorPath}
      state={{ resource }} aria-label={t('myResources.editResource', { name: resource.metadata.name })}>
      {content}
    </Link>
  )
}

export function MyResourcesPage() {
  const { t } = useTranslation()
  const { user, isLoading: isAuthLoading } = useAuth()
  const location = useLocation()
  const [selectedType, setSelectedType] = useState('')
  const [resources, setResources] = useState([])
  const [nextOffset, setNextOffset] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ author: user.username, limit: 50 })
      .then((page) => { if (active) { setResources(page.items); setNextOffset(page.nextOffset) } })
      .catch(() => { if (active) setError(t('myResources.loadFailed')) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [t, user])

  useEffect(() => {
    document.title = `${t('myResources.title')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [t])

  if (!isAuthLoading && !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  const visibleResources = selectedType
    ? resources.filter((resource) => resource.resourceType === selectedType)
    : resources

  async function loadMore() {
    if (nextOffset === null) return
    setIsLoading(true); setError('')
    try {
      const page = await listResources({ author: user.username, limit: 50, offset: nextOffset })
      setResources((current) => [...current, ...page.items]); setNextOffset(page.nextOffset)
    } catch { setError(t('myResources.loadFailed')) }
    finally { setIsLoading(false) }
  }

  return (
    <section className="my-resources-page" aria-labelledby="my-resources-heading">
      <div className="my-resources-heading">
        <span className="eyebrow">{t('myResources.library')}</span>
        <h1 id="my-resources-heading">{t('myResources.title')}</h1>
        <p>{t('myResources.description')}</p>
      </div>
      <div className="resource-tabs" role="tablist" aria-label={t('home.resourceTypes')}>
        {RESOURCE_TABS.map((tab) => (
          <button key={tab.label} type="button" role="tab"
            aria-selected={selectedType === tab.value}
            className={selectedType === tab.value ? 'active' : ''}
            onClick={() => setSelectedType(tab.value)}>
            {t(`home.tabs.${tab.label}`)}
          </button>
        ))}
      </div>
      {isAuthLoading || isLoading ? (
        <div className="catalogue-message" role="status">{t('myResources.loading')}</div>
      ) : error ? (
        <div className="catalogue-message error" role="alert">{error}</div>
      ) : visibleResources.length === 0 ? (
        <div className="catalogue-message empty">
          <span aria-hidden="true">◇</span><h2>{t('myResources.emptyTitle')}</h2>
          <p>{t('myResources.emptyDescription')}</p>
        </div>
      ) : (
        <div className="resource-grid my-resource-grid">
          {visibleResources.map((resource) => (
            <PersonalResourceCard key={resource.id} resource={resource} />
          ))}
        </div>
      )}
      {resources.length > 0 && nextOffset !== null && (
        <button className="load-more-button" type="button" disabled={isLoading} onClick={loadMore}>
          {isLoading ? t('home.loadingMore') : t('home.loadMore')}
        </button>
      )}
    </section>
  )
}
