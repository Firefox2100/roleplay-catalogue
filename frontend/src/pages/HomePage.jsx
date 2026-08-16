import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listResources } from '../api/resources.js'

const RESOURCE_TABS = [
  { value: '', label: 'all' },
  { value: 'sillytavern/character', label: 'characters' },
  { value: 'sillytavern/lorebook', label: 'lorebooks' },
  { value: 'core/image', label: 'images' },
]

function ResourceCard({ resource }) {
  const { t } = useTranslation()
  const description = resource.metadata.description || t('home.noDescription')

  return (
    <article className="catalogue-card" tabIndex="0">
      <div className="resource-cover-placeholder" aria-label={t('home.imagePlaceholder')}>
        <span aria-hidden="true">◇</span>
      </div>
      <h2>{resource.metadata.name}</h2>
      <div className="resource-description-tooltip" role="tooltip">{description}</div>
    </article>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const [selectedType, setSelectedType] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [authorInput, setAuthorInput] = useState('')
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
      tags: tagInput.split(',').map((tag) => tag.trim()).filter(Boolean),
      author: authorInput.trim(),
    })
  }

  function clearFilters() {
    setIsLoading(true)
    setError('')
    setTagInput('')
    setAuthorInput('')
    setFilters({ tags: [], author: '' })
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
            <input id="filter-tags" value={tagInput}
              onChange={(event) => setTagInput(event.target.value)}
              placeholder={t('home.tagsPlaceholder')} />
            <p className="field-help">{t('home.tagsHelp')}</p>
            <label htmlFor="filter-author">{t('home.author')}</label>
            <input id="filter-author" value={authorInput}
              onChange={(event) => setAuthorInput(event.target.value)}
              placeholder={t('home.authorPlaceholder')} />
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
              {resources.map((resource) => <ResourceCard key={resource.id} resource={resource} />)}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
