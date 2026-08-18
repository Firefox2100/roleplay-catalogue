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
  { value: 'sillytavern/preset', label: 'presets' },
  { value: 'core/image', label: 'images' },
  { value: 'world-simulation-engine/world', label: 'worlds' },
]

function ResourceCard({ resource, onSelectAuthor }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const description = resource.metadata.description || t('home.noDescription')
  const imageUrl = resourceImageUrl(resource)
  const detailPath = resource.resourceType === 'core/image'
    ? `/images/${resource.id}`
    : resource.resourceType === 'sillytavern/character'
      ? `/characters/${resource.id}`
      : resource.resourceType === 'sillytavern/lorebook' ? `/lorebooks/${resource.id}` : ''
  const presetDetailPath = resource.resourceType === 'sillytavern/preset'
    ? `/presets/${resource.id}` : detailPath
  const resolvedDetailPath = resource.resourceType === 'world-simulation-engine/world'
    ? `/worlds/${resource.id}` : presetDetailPath

  return (
    <article className={`catalogue-card${resolvedDetailPath ? ' clickable' : ''}`}
      tabIndex={resolvedDetailPath ? '0' : undefined} role={resolvedDetailPath ? 'link' : undefined}
      onClick={() => resolvedDetailPath && navigate(resolvedDetailPath)}
      onKeyDown={(event) => {
        if (resolvedDetailPath && (event.key === 'Enter' || event.key === ' ')) event.currentTarget.click()
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
      {resource.metadata.tags?.length > 0 && (
        <div className="resource-card-tags" aria-label={t('resource.tags')}>
          {resource.metadata.tags.slice(0, 3).map((tag) => (
            <span key={tag} title={tag}>{tag}</span>
          ))}
          {resource.metadata.tags.length > 3 && (
            <span title={resource.metadata.tags.slice(3).join(', ')}>
              +{resource.metadata.tags.length - 3}
            </span>
          )}
        </div>
      )}
      <div className="resource-description-tooltip" role="tooltip">{description}</div>
    </article>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const [selectedType, setSelectedType] = useState('')
  const [selectedTags, setSelectedTags] = useState([])
  const [filters, setFilters] = useState({ tags: [], author: '', searchString: '' })
  const [search, setSearch] = useState('')
  const [resources, setResources] = useState([])
  const [nextOffset, setNextOffset] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listResources({ resourceType: selectedType, publishedOnly: true, ...filters })
      .then((page) => { if (active) { setResources(page.items); setNextOffset(page.nextOffset) } })
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
      searchString: filters.searchString,
    })
  }

  function clearFilters() {
    setIsLoading(true)
    setError('')
    setSelectedTags([])
    setSearch('')
    setFilters({ tags: [], author: '', searchString: '' })
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

  function submitSearch(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    setFilters((current) => ({ ...current, searchString: search.trim() }))
  }

  async function loadMore() {
    if (nextOffset === null) return
    setIsLoading(true); setError('')
    try {
      const page = await listResources({
        resourceType: selectedType, publishedOnly: true, ...filters, offset: nextOffset,
      })
      setResources((current) => [...current, ...page.items])
      setNextOffset(page.nextOffset)
    } catch { setError(t('home.loadFailed')) }
    finally { setIsLoading(false) }
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
          <form className="catalogue-search" onSubmit={submitSearch}>
            <span aria-hidden="true">⌕</span>
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
              placeholder={t('home.searchPlaceholder')} aria-label={t('home.searchPlaceholder')} />
            <button type="submit">{t('home.search')}</button>
          </form>
          {isLoading && resources.length === 0 ? (
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
          {resources.length > 0 && nextOffset !== null && (
            <button className="load-more-button" type="button" disabled={isLoading} onClick={loadMore}>
              {isLoading ? t('home.loadingMore') : t('home.loadMore')}
            </button>
          )}
        </div>
      </div>
    </section>
  )
}
