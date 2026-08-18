import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { getResource, getResourceVersionData, listResourceVersions, versionDownloadUrl } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'

export function PresetDetailPage() {
  const { resourceId } = useParams(); const { t } = useTranslation(); const { user } = useAuth()
  const [resource, setResource] = useState(null); const [versions, setVersions] = useState([])
  const [selected, setSelected] = useState(''); const [data, setData] = useState(null); const [error, setError] = useState('')
  useEffect(() => { Promise.all([getResource(resourceId), listResourceVersions(resourceId)]).then(([item, releases]) => { if (item.resourceType !== 'sillytavern/preset' || !releases.length) throw new Error(); setResource(item); setVersions(releases); setSelected(releases[0].id) }).catch(() => setError(t('preset.loadFailed'))) }, [resourceId, t])
  useEffect(() => { if (selected) getResourceVersionData(selected).then((document) => setData(document.data)).catch(() => setError(t('preset.loadFailed'))) }, [selected, t])
  if (error) return <div className="page-loading error">{error}</div>
  if (!resource || !data) return <div className="page-loading">{t('preset.loading')}</div>
  return <section className="character-editor-page"><div className="character-editor"><header className="editor-toolbar"><div><span className="eyebrow">{t('preset.publishedPreset')}</span><h1>{resource.metadata.name}</h1></div><div className="detail-version-actions"><select value={selected} onChange={(event) => { setData(null); setSelected(event.target.value) }}>{versions.map((version) => <option key={version.id} value={version.id}>{version.version}</option>)}</select><a className="save-button" href={versionDownloadUrl(selected)}>{t('details.download')}</a>{user?.id === resource.authorId && <Link className="save-button" to={`/presets/${resource.id}/edit`}>{t('preset.edit')}</Link>}</div></header>
    <section className="resource-metadata-editor detail-metadata"><h2>{t('editor.resourceMetadata')}</h2><p>{resource.metadata.description}</p><div className="detail-tags">{resource.metadata.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></section>
    <section className="preset-settings"><h2>{t('preset.sampling')}</h2><div className="world-count-grid">{SAMPLING_FIELDS.map((field) => <div key={field}><strong>{String(data[field])}</strong><span>{t(`preset.fields.${field}`)}</span></div>)}</div></section>
    <section className="preset-prompts"><h2>{t('preset.prompts')}</h2>{data.prompts.map((prompt) => <article className="preset-prompt" key={prompt.identifier}><h3>{prompt.name || prompt.identifier}</h3>{prompt.marker ? <small>{t('preset.marker')}</small> : <><small>{prompt.role}</small><p>{prompt.content}</p></>}</article>)}</section>
  </div></section>
}

const SAMPLING_FIELDS = ['temperature', 'top_p', 'top_k', 'min_p', 'repetition_penalty', 'openai_max_context', 'openai_max_tokens']
