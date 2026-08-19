import { useTranslation } from 'react-i18next'

function diffLineClass(line) {
  if (line.startsWith('+++') || line.startsWith('---')) return 'diff-meta'
  if (line.startsWith('@@')) return 'diff-hunk'
  if (line.startsWith('+')) return 'diff-add'
  if (line.startsWith('-')) return 'diff-remove'
  return 'diff-context'
}

export function ReleaseDiff({ diff }) {
  const { t } = useTranslation()
  if (!diff) return null

  const lines = diff.replace(/\n$/, '').split('\n')
  const additions = lines.filter((line) => line.startsWith('+') && !line.startsWith('+++')).length
  const deletions = lines.filter((line) => line.startsWith('-') && !line.startsWith('---')).length

  return (
    <details className="release-diff">
      <summary>
        <span>{t('details.diffSummary')}</span>
        <span className="diff-stat-add">{t('details.diffAdditions', { count: additions })}</span>
        <span className="diff-stat-remove">{t('details.diffDeletions', { count: deletions })}</span>
      </summary>
      <pre className="diff-viewer">
        {lines.map((line, index) => (
          <span className={`diff-line ${diffLineClass(line)}`} key={index}>{line || ' '}</span>
        ))}
      </pre>
    </details>
  )
}
