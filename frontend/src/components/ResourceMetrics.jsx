import { useTranslation } from 'react-i18next'


export function ResourceMetrics({ resource, compact = false }) {
  const { t, i18n } = useTranslation()
  const format = (value) => Number(value ?? 0).toLocaleString(i18n.language)
  return (
    <div className={`resource-metrics${compact ? ' compact' : ''}`}
      aria-label={t('metrics.engagement')}>
      <span title={t('metrics.views')}><span aria-hidden="true">◉</span> {format(resource.viewCount)}</span>
      <span title={t('metrics.downloads')}><span aria-hidden="true">⇩</span> {format(resource.downloadCount)}</span>
    </div>
  )
}
