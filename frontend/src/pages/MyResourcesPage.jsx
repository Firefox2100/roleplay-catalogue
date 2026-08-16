import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { listResources } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'

const RESOURCE_TABS = [
  { value: '', label: 'all' },
  { value: 'sillytavern/character', label: 'characters' },
  { value: 'sillytavern/lorebook', label: 'lorebooks' },
  { value: 'core/image', label: 'images' },
]

function PersonalResourceCard({ resource }) {
  const { t } = useTranslation()
  const isEditable = resource.resourceType === 'sillytavern/character'
  const content = (
    <article className={`catalogue-card ${isEditable ? 'editable' : 'unavailable'}`}>
      <div className="resource-cover-placeholder" aria-label={t('home.imagePlaceholder')}>
        <span aria-hidden="true">◇</span>
      </div>
      <h2>{resource.metadata.name}</h2>
      {!isEditable && <small className="not-editable-label">{t('myResources.editorComingSoon')}</small>}
      <div className="resource-description-tooltip" role="tooltip">
        {resource.metadata.description || t('home.noDescription')}
      </div>
    </article>
  )

  if (!isEditable) return content
  return (
    <Link className="my-resource-link" to={`/resources/${resource.id}/edit`}
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
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return undefined
    let active = true
    listResources({ author: user.username, limit: 100 })
      .then((items) => { if (active) setResources(items) })
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
    </section>
  )
}
