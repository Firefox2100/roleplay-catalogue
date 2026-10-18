import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { listResources, resourceImageUrl } from '../api/resources.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { ResourceMetrics } from '../components/ResourceMetrics.jsx'
import { TagEditor } from '../components/TagEditor.jsx'

const RESOURCE_TABS = [
  { value: '', label: 'all' }, { value: 'sillytavern/character', label: 'characters' },
  { value: 'sillytavern/lorebook', label: 'lorebooks' },
  { value: 'sillytavern/preset', label: 'presets' }, { value: 'core/image', label: 'images' },
  { value: 'world-simulation-engine/world', label: 'worlds' },
]

function resourcePath(resource) {
  const prefix = { 'core/image': 'images', 'sillytavern/character': 'characters',
    'sillytavern/lorebook': 'lorebooks', 'sillytavern/preset': 'presets',
    'world-simulation-engine/world': 'worlds' }[resource.resourceType]
  return prefix ? `/${prefix}/${resource.id}` : '/'
}

function ResourceCover({ resource }) {
  const { t } = useTranslation()
  const imageUrl = resourceImageUrl(resource)
  return imageUrl ? <ResourceImage className="archive-cover" src={imageUrl} /> : (
    <div className="archive-cover archive-cover-placeholder" aria-label={t('home.imagePlaceholder')}>
      <svg aria-hidden="true" viewBox="0 0 48 48"><path d="M9 36 20 25l7 7 5-5 7 9M15 17h.1" /></svg>
    </div>
  )
}

function TypeLabel({ resource }) {
  const { t } = useTranslation()
  const tab = RESOURCE_TABS.find(({ value }) => value === resource.resourceType)
  return <span className="archive-type">{t(`home.tabs.${tab?.label || 'all'}`)}</span>
}

function RecentRelease({ resource }) {
  const { t, i18n } = useTranslation()
  const updatedAt = resource.updatedAt ? new Date(resource.updatedAt) : null
  return <Link className="recent-release" to={resourcePath(resource)}>
    <ResourceCover resource={resource} />
    <span className="release-copy"><TypeLabel resource={resource} />
      <strong>{resource.metadata.name}</strong>
      <span>{t('home.byAuthor', { author: resource.authorUsername })}</span>
      {updatedAt && <time dateTime={resource.updatedAt}>{t('home.updated', {
        date: new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium' }).format(updatedAt),
      })}</time>}
    </span>
  </Link>
}

function PopularResource({ resource, rank }) {
  const { t } = useTranslation()
  return <article className="popular-resource">
    <Link className="popular-resource-main" to={resourcePath(resource)}>
      <ResourceCover resource={resource} />
      <span className="popular-copy"><TypeLabel resource={resource} />
        <strong>{resource.metadata.name}</strong>
        <span>{resource.metadata.description || t('home.noDescription')}</span>
        <ResourceMetrics resource={resource} compact />
      </span>
    </Link>
    <span className="popular-rank" aria-label={t('home.rank', { rank })}>{rank}</span>
  </article>
}

function CatalogueCard({ resource, onSelectAuthor }) {
  const { t } = useTranslation()
  return <article className="catalogue-card archive-catalogue-card">
    <Link className="catalogue-card-main" to={resourcePath(resource)}>
      <ResourceCover resource={resource} /><TypeLabel resource={resource} />
      <h2>{resource.metadata.name}</h2>
    </Link>
    <button className="resource-author" type="button"
      onClick={() => onSelectAuthor(resource.authorUsername)}>{resource.authorUsername}</button>
    <ResourceMetrics resource={resource} compact />
    {resource.metadata.tags?.length > 0 && <div className="resource-card-tags" aria-label={t('resource.tags')}>
      {resource.metadata.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}
    </div>}
  </article>
}

export function HomePage() {
  const { t } = useTranslation()
  const [selectedType, setSelectedType] = useState('')
  const [selectedTags, setSelectedTags] = useState([])
  const [filters, setFilters] = useState({ tags: [], author: '', searchString: '' })
  const [search, setSearch] = useState('')
  const [resources, setResources] = useState([])
  const [recentResources, setRecentResources] = useState([])
  const [popularResources, setPopularResources] = useState([])
  const [nextOffset, setNextOffset] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [requestVersion, setRequestVersion] = useState(0)

  useEffect(() => {
    let active = true
    listResources({ resourceType: selectedType, publishedOnly: true, limit: 50, ...filters })
      .then((page) => { if (active) { setResources(page.items); setNextOffset(page.nextOffset); setError('') } })
      .catch(() => { if (active) setError(t('home.loadFailed')) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [filters, requestVersion, selectedType, t])

  useEffect(() => {
    let active = true
    Promise.all([
      listResources({ publishedOnly: true, limit: 4 }),
      listResources({ publishedOnly: true, limit: 3, sort: 'popular' }),
    ]).then(([recentPage, popularPage]) => {
      if (active) { setRecentResources(recentPage.items); setPopularResources(popularPage.items) }
    }).catch(() => {})
    return () => { active = false }
  }, [requestVersion])

  const popular = useMemo(() => popularResources, [popularResources])
  const recent = useMemo(() => recentResources, [recentResources])
  const hasActiveFilters = Boolean(selectedType || selectedTags.length || filters.author ||
    filters.searchString)

  function applyFilters(event) {
    event.preventDefault()
    setIsLoading(true)
    setFilters((current) => ({ ...current, tags: selectedTags, searchString: search.trim() }))
  }

  function clearFilters() {
    setIsLoading(true)
    setSelectedTags([]); setSearch(''); setSelectedType('')
    setFilters({ tags: [], author: '', searchString: '' })
  }

  async function loadMore() {
    if (nextOffset === null) return
    setIsLoading(true)
    try {
      const page = await listResources({ resourceType: selectedType, publishedOnly: true,
        limit: 50, ...filters, offset: nextOffset })
      setResources((current) => [...current, ...page.items]); setNextOffset(page.nextOffset)
    } catch { setError(t('home.loadFailed')) }
    finally { setIsLoading(false) }
  }

  return <div className="home-page">
    <section className="archive-intro" aria-labelledby="catalogue-heading">
      <div><h1 id="catalogue-heading">{t('home.title')}</h1><p>{t('home.introduction')}</p>
        {recent.length > 0 && <p className="fresh-note"><span aria-hidden="true" />{t('home.freshNote')}</p>}
      </div>
    </section>

    {!error && recent.length > 0 && <section className="archive-section" aria-labelledby="recent-heading">
      <div className="archive-section-heading"><div><h2 id="recent-heading">{t('home.recentTitle')}</h2>
        <p>{t('home.recentDescription')}</p></div></div>
      <div className="recent-releases">{recent.map((resource) =>
        <RecentRelease key={resource.id} resource={resource} />)}</div>
    </section>}

    {!error && popular.length > 0 && <section className="archive-section" aria-labelledby="popular-heading">
      <div className="archive-section-heading"><div><h2 id="popular-heading">{t('home.popularTitle')}</h2>
        <p>{t('home.popularDescription')}</p></div></div>
      <div className="popular-resources">{popular.map((resource, index) =>
        <PopularResource key={resource.id} resource={resource} rank={index + 1} />)}</div>
    </section>}

    <section className="archive-browse" aria-labelledby="browse-heading">
      <div className="browse-heading"><div><h2 id="browse-heading">{t('home.browseTitle')}</h2>
        <p>{t('home.browseDescription')}</p></div></div>
      <form className="archive-search" onSubmit={applyFilters}>
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
          placeholder={t('home.searchPlaceholder')} aria-label={t('home.searchPlaceholder')} />
        <select value={selectedType} onChange={(event) => { setIsLoading(true); setSelectedType(event.target.value) }}
          aria-label={t('home.typeLabel')}>
          {RESOURCE_TABS.map((tab) => <option key={tab.label} value={tab.value}>
            {tab.value ? t(`home.tabs.${tab.label}`) : t('home.allTypes')}</option>)}
        </select>
        <button type="submit">{t('home.search')}</button>
        <div className="archive-tag-filter"><TagEditor value={selectedTags} onChange={setSelectedTags}
          allowCreate={false} showPopular /></div>
      </form>
      {filters.author && <div className="active-filter archive-active-filter">
        <span>{t('home.authorFilter', { author: filters.author })}</span>
        <button type="button" aria-label={t('home.removeAuthorFilter')}
          onClick={() => { setIsLoading(true); setFilters((current) => ({ ...current, author: '' })) }}>×</button>
      </div>}
      {isLoading && resources.length === 0 ? <div className="catalogue-message" role="status">{t('home.loading')}</div>
        : error ? <div className="catalogue-message error" role="alert"><p>{error}</p>
          <button type="button" onClick={() => { setIsLoading(true); setRequestVersion((value) => value + 1) }}>{t('home.retry')}</button></div>
          : resources.length === 0 ? <div className="catalogue-message empty">
            <h2>{t(hasActiveFilters ? 'home.emptyTitle' : 'home.emptyArchiveTitle')}</h2>
            <p>{t(hasActiveFilters ? 'home.emptyDescription' : 'home.emptyArchiveDescription')}</p>
            {hasActiveFilters ? <button type="button" onClick={clearFilters}>{t('home.clearFilters')}</button>
              : <Link className="empty-create-link" to="/resources/new">{t('home.createFirst')}</Link>}
          </div>
            : <div className="resource-grid">{resources.map((resource) => <CatalogueCard key={resource.id}
              resource={resource} onSelectAuthor={(author) => { setIsLoading(true); setFilters((current) => ({ ...current, author })) }} />)}</div>}
      {resources.length > 0 && nextOffset !== null && <button className="load-more-button" type="button"
        disabled={isLoading} onClick={loadMore}>{isLoading ? t('home.loadingMore') : t('home.loadMore')}</button>}
    </section>
  </div>
}
