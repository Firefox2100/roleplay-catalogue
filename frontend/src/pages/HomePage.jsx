import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { listResources, resourceImageUrl } from '../api/resources.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { TagEditor } from '../components/TagEditor.jsx'

const RESOURCE_TABS = [
  { value: '', label: 'all' },
  { value: 'sillytavern/character', label: 'characters' },
  { value: 'sillytavern/lorebook', label: 'lorebooks' },
  { value: 'core/image', label: 'images' },
]

function ResourceCard({ resource, onSelectAuthor }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const description = resource.metadata.description || t('home.noDescription')
  const imageUrl = resourceImageUrl(resource)
  const detailPath = resource.resourceType === 'core/image'
    ? `/images/${resource.id}`
    : resource.resourceType === 'sillytavern/character' ? `/characters/${resource.id}` : ''

  return (
    <article className={`catalogue-card${detailPath ? ' clickable' : ''}`}
      tabIndex={detailPath ? '0' : undefined} role={detailPath ? 'link' : undefined}
      onClick={() => detailPath && navigate(detailPath)}
      onKeyDown={(event) => {
        if (detailPath && (event.key === 'Enter' || event.key === ' ')) event.currentTarget.click()
      }}>
      {imageUrl ? (
        <ResourceImage className="resource-grid-image" src={imageUrl} />
      ) : (
        <div className="resource-cover-placeholder" aria-label={t('home.imagePlaceholder')}>
          <span aria-hidden="true">◇</span>
        </div>
      )}
      <h2>{resource.metadata.name}</h2>
      <button className="resource-author" type="button"
        onClick={(event) => { event.stopPropagation(); onSelectAuthor(resource.authorUsername) }}>
        {resource.authorUsername}
      </button>
      <div className="resource-description-tooltip" role="tooltip">{description}</div>
    </article>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const [selectedType, setSelectedType] = useState('')
  const [selectedTags, setSelectedTags] = useState([])
  const [filters, setFilters] = useState({ tags: [], author: '' })
  const [search, setSearch] = useState('')
  const [resources, setResources] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listResources({ resourceType: selectedType, publishedOnly: true, ...filters })
      .then((items) => { if (active) setResources(items) })
      .catch(() => { if (active) setError(t('home.loadFailed')) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [filters, selectedType, t])

  function applyFilters(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    setFilters({
      tags: selectedTags,
      author: filters.author,
    })
  }

  function clearFilters() {
    setIsLoading(true)
    setError('')
    setSelectedTags([])
    setFilters({ tags: [], author: '' })
  }

  function selectAuthor(author) {
    setIsLoading(true)
    setError('')
    setFilters((current) => ({ ...current, author }))
  }

  function clearAuthor() {
    setIsLoading(true)
    setError('')
    setFilters((current) => ({ ...current, author: '' }))
  }

  function selectType(resourceType) {
    setIsLoading(true)
    setError('')
    setSelectedType(resourceType)
  }

  return (
    <section className="home-page" aria-labelledby="catalogue-heading">
      <h1 id="catalogue-heading" className="visually-hidden">{t('home.label')}</h1>
      <div className="resource-tabs" role="tablist" aria-label={t('home.resourceTypes')}>
        {RESOURCE_TABS.map((tab) => (
          <button key={tab.label} type="button" role="tab"
            aria-selected={selectedType === tab.value}
            className={selectedType === tab.value ? 'active' : ''}
            onClick={() => selectType(tab.value)}>
            {t(`home.tabs.${tab.label}`)}
          </button>
        ))}
      </div>

      <div className="catalogue-layout">
        <aside className="catalogue-filters" aria-labelledby="filter-heading">
          <h2 id="filter-heading">{t('home.filters')}</h2>
          <form onSubmit={applyFilters}>
            <label htmlFor="filter-tags">{t('resource.tags')}</label>
            <TagEditor id="filter-tags" value={selectedTags} onChange={setSelectedTags}
              allowCreate={false} showPopular />
            {filters.author && (
              <div className="active-filter">
                <span>{t('home.authorFilter', { author: filters.author })}</span>
                <button type="button" aria-label={t('home.removeAuthorFilter')}
                  onClick={clearAuthor}>×</button>
              </div>
            )}
            <button className="filter-button" type="submit">{t('home.applyFilters')}</button>
            <button className="clear-filter-button" type="button" onClick={clearFilters}>
              {t('home.clearFilters')}
            </button>
          </form>
        </aside>

        <div className="catalogue-results">
          <div className="catalogue-search">
            <span aria-hidden="true">⌕</span>
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
              placeholder={t('home.searchPlaceholder')} aria-label={t('home.searchPlaceholder')} />
            <small>{t('home.searchComingSoon')}</small>
          </div>
          {isLoading ? (
            <div className="catalogue-message" role="status">{t('home.loading')}</div>
          ) : error ? (
            <div className="catalogue-message error" role="alert">{error}</div>
          ) : resources.length === 0 ? (
            <div className="catalogue-message empty">
              <span aria-hidden="true">◇</span><h2>{t('home.emptyTitle')}</h2>
              <p>{t('home.emptyDescription')}</p>
            </div>
          ) : (
            <div className="resource-grid">
              {resources.map((resource) => (
                <ResourceCard key={resource.id} resource={resource} onSelectAuthor={selectAuthor} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
