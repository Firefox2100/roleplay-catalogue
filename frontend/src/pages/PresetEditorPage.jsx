import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import {
  deleteResource, draftDownloadUrl, getResource, getResourceData, importPreset,
  listResourceVersions, publishResource, saveResourceData, updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { TagEditor } from '../components/TagEditor.jsx'

const DEFAULT_DATA = {
  temperature: 1, frequency_penalty: 0, presence_penalty: 0, top_p: 1, top_k: 0,
  top_a: 0, min_p: 0, repetition_penalty: 1, openai_max_context: 4095,
  openai_max_tokens: 300, seed: -1, n: 1, stream_openai: true,
  prompts: [], prompt_order: [{ character_id: 100000, order: [] }],
}
const SAMPLERS = ['temperature', 'frequency_penalty', 'presence_penalty', 'top_p', 'top_k', 'top_a', 'min_p', 'repetition_penalty', 'openai_max_context', 'openai_max_tokens', 'seed', 'n']
const KNOWN = new Set([...SAMPLERS, 'stream_openai', 'prompts', 'prompt_order'])

function JsonEditor({ value, onChange }) {
  const [text, setText] = useState(JSON.stringify(value, null, 2))
  useEffect(() => setText(JSON.stringify(value, null, 2)), [value])
  return <textarea className="world-json-field" rows={12} value={text}
    onChange={(event) => setText(event.target.value)} onBlur={() => {
      try { const parsed = JSON.parse(text); if (parsed && !Array.isArray(parsed)) onChange(parsed) } catch { /* retain text */ }
    }} />
}

export function PresetEditorPage() {
  const { resourceId } = useParams()
  const location = useLocation()
  const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth()
  const fileInput = useRef(null)
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [metadata, setMetadata] = useState(null)
  const [data, setData] = useState(DEFAULT_DATA)
  const [versions, setVersions] = useState([])
  const [releaseVersion, setReleaseVersion] = useState('v1.0.0')
  const [busy, setBusy] = useState('load')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    let active = true
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)])
      .then(async ([loaded, releases]) => {
        if (loaded.resourceType !== 'sillytavern/preset') throw new Error('wrong type')
        if (!active) return
        setResource(loaded); setMetadata({ ...loaded.metadata, tags: [...loaded.metadata.tags] }); setVersions(releases)
        try { const draft = await getResourceData(resourceId); if (active) setData({ ...DEFAULT_DATA, ...draft.data }) }
        catch (requestError) { if (requestError.status !== 404) throw requestError }
      }).catch(() => active && setError(t('preset.loadFailed')))
      .finally(() => active && setBusy(''))
    return () => { active = false }
  }, [resourceId, user, t])

  const advanced = useMemo(() => Object.fromEntries(Object.entries(data).filter(([key]) => !KNOWN.has(key))), [data])
  if (!authLoading && !user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (authLoading || busy === 'load') return <div className="page-loading">{t('preset.loading')}</div>
  if (!resource || !metadata) return <div className="page-loading error">{error || t('preset.loadFailed')}</div>

  function setPrompt(index, field, value) {
    setData((current) => ({ ...current, prompts: current.prompts.map((prompt, i) => i === index ? { ...prompt, [field]: value } : prompt) }))
  }
  function addPrompt() {
    const identifier = `custom-${crypto.randomUUID()}`
    setData((current) => ({
      ...current,
      prompts: [...current.prompts, { identifier, name: '', system_prompt: false, marker: false, role: 'system', content: '' }],
      prompt_order: (current.prompt_order.length ? current.prompt_order : [{ character_id: 100000, order: [] }]).map((group) => ({ ...group, order: [...group.order, { identifier, enabled: true }] })),
    }))
  }
  function removePrompt(identifier) {
    setData((current) => ({ ...current, prompts: current.prompts.filter((prompt) => prompt.identifier !== identifier), prompt_order: current.prompt_order.map((group) => ({ ...group, order: group.order.filter((item) => item.identifier !== identifier) })) }))
  }
  function setEnabled(identifier, enabled) {
    setData((current) => ({ ...current, prompt_order: current.prompt_order.map((group) => ({ ...group, order: group.order.map((item) => item.identifier === identifier ? { ...item, enabled } : item) })) }))
  }
  function movePrompt(index, direction) {
    const target = index + direction
    if (target < 0 || target >= data.prompts.length) return
    const prompts = [...data.prompts]; [prompts[index], prompts[target]] = [prompts[target], prompts[index]]
    const rank = new Map(prompts.map((prompt, promptIndex) => [prompt.identifier, promptIndex]))
    setData({ ...data, prompts, prompt_order: data.prompt_order.map((group) => ({ ...group, order: [...group.order].sort((a, b) => (rank.get(a.identifier) ?? 9999) - (rank.get(b.identifier) ?? 9999)) })) })
  }
  async function persist() {
    const updated = await updateResource(resourceId, metadata)
    await saveResourceData(resourceId, data)
    setResource(updated)
  }
  async function save() {
    setBusy('save'); setError(''); setMessage('')
    try { await persist(); setMessage(t('preset.saved')) } catch { setError(t('preset.saveFailed')) } finally { setBusy('') }
  }
  async function publish() {
    setBusy('publish'); setError(''); setMessage('')
    try { await persist(); const version = await publishResource(resourceId, releaseVersion); setVersions((items) => [version, ...items]); setMessage(t('preset.published')) }
    catch { setError(t('preset.publishFailed')) } finally { setBusy('') }
  }
  async function upload(file) {
    if (!file) return
    setBusy('import'); setError('')
    try { const result = await importPreset(resourceId, file); setData({ ...DEFAULT_DATA, ...result.draft.data }); setMessage(t('preset.imported')) }
    catch { setError(t('preset.importFailed')) } finally { setBusy(''); fileInput.current.value = '' }
  }

  const order = data.prompt_order?.[0]?.order ?? []
  return <section className="character-editor-page"><div className="character-editor">
    <header className="editor-toolbar"><div><span className="eyebrow">{t('preset.draft')}</span><h1>{metadata.name}</h1></div><div className="editor-actions">
      <button className="danger-button" type="button" onClick={async () => { if (confirm(t('editor.deleteConfirm'))) { await deleteResource(resourceId, resource.resourceType); window.location.assign('/resources/mine') } }}>{t('editor.delete')}</button>
      <button type="button" onClick={() => fileInput.current?.click()}>{t('editor.upload')}</button><a className="editor-action-link" href={draftDownloadUrl(resourceId)}>{t('editor.export')}</a>
      <button className="save-button" type="button" disabled={Boolean(busy)} onClick={save}>{busy === 'save' ? t('editor.saving') : t('editor.save')}</button>
    </div></header>
    <input hidden ref={fileInput} type="file" accept=".json,application/json" onChange={(event) => upload(event.target.files?.[0])} />
    {error && <p className="editor-message error">{error}</p>}{message && <p className="editor-message success">{message}</p>}
    <section className="resource-metadata-editor"><h2>{t('editor.resourceMetadata')}</h2><div className="editor-field-grid">
      <label>{t('resource.name')}<input value={metadata.name} onChange={(event) => setMetadata({ ...metadata, name: event.target.value })} /></label>
      <label>{t('resource.visibility')}<select value={metadata.visibility} onChange={(event) => setMetadata({ ...metadata, visibility: event.target.value })}>{['private', 'authenticated', 'public'].map((item) => <option key={item} value={item}>{t(`resource.visibilities.${item}`)}</option>)}</select></label>
      <label>{t('resource.language')}<select value={metadata.language} onChange={(event) => setMetadata({ ...metadata, language: event.target.value })}><option value="en-uk">{t('resource.languages.enUK')}</option><option value="zh-cn">{t('resource.languages.zhCN')}</option></select></label>
      <label className="wide-field">{t('resource.description')}<textarea rows={3} value={metadata.description} onChange={(event) => setMetadata({ ...metadata, description: event.target.value })} /></label>
      <div className="wide-field"><label>{t('resource.tags')}</label><TagEditor value={metadata.tags} onChange={(tags) => setMetadata({ ...metadata, tags })} /></div>
    </div></section>
    <section className="preset-settings"><h2>{t('preset.sampling')}</h2><div className="editor-field-grid">{SAMPLERS.map((field) => <label key={field}>{t(`preset.fields.${field}`)}<input type="number" step="any" value={data[field]} onChange={(event) => setData({ ...data, [field]: Number(event.target.value) })} /></label>)}
      <label className="checkbox-field"><input type="checkbox" checked={data.stream_openai} onChange={(event) => setData({ ...data, stream_openai: event.target.checked })} />{t('preset.fields.stream_openai')}</label></div></section>
    <section className="preset-prompts"><div className="section-heading"><div><h2>{t('preset.prompts')}</h2><p>{t('preset.promptsHelp')}</p></div><button className="add-list-button" type="button" onClick={addPrompt}>＋ {t('preset.addPrompt')}</button></div>
      {data.prompts.map((prompt, index) => <article className="preset-prompt" key={prompt.identifier}><div className="preset-prompt-heading"><strong>{prompt.name || prompt.identifier}</strong><div><button type="button" onClick={() => movePrompt(index, -1)}>↑</button><button type="button" onClick={() => movePrompt(index, 1)}>↓</button><button type="button" onClick={() => removePrompt(prompt.identifier)}>{t('editor.remove')}</button></div></div><div className="editor-field-grid">
        <label>{t('preset.promptName')}<input value={prompt.name} onChange={(event) => setPrompt(index, 'name', event.target.value)} /></label>
        <label>{t('preset.identifier')}<input value={prompt.identifier} readOnly /></label>
        <label>{t('preset.role')}<select value={prompt.role ?? 'system'} onChange={(event) => setPrompt(index, 'role', event.target.value)}><option value="system">system</option><option value="user">user</option><option value="assistant">assistant</option></select></label>
        <label className="checkbox-field"><input type="checkbox" checked={order.find((item) => item.identifier === prompt.identifier)?.enabled ?? true} onChange={(event) => setEnabled(prompt.identifier, event.target.checked)} />{t('preset.enabled')}</label>
        <label className="checkbox-field"><input type="checkbox" checked={prompt.marker ?? false} onChange={(event) => setPrompt(index, 'marker', event.target.checked)} />{t('preset.marker')}</label>
        <label className="wide-field">{t('preset.content')}<textarea rows={6} disabled={prompt.marker} value={prompt.content ?? ''} onChange={(event) => setPrompt(index, 'content', event.target.value)} /></label>
      </div></article>)}</section>
    <section className="preset-settings"><h2>{t('preset.advanced')}</h2><p>{t('preset.advancedHelp')}</p><JsonEditor value={advanced} onChange={(value) => setData({ ...Object.fromEntries(Object.entries(data).filter(([key]) => KNOWN.has(key))), ...value })} /></section>
    <section className="release-history"><h2>{t('editor.releases')}</h2><div className="world-publish-row"><input value={releaseVersion} onChange={(event) => setReleaseVersion(event.target.value)} /><button className="save-button" disabled={Boolean(busy)} type="button" onClick={publish}>{t('editor.publish')}</button></div><div className="release-grid">{versions.map((version) => <div className="release-tile" key={version.id}><strong>{version.version}</strong></div>)}</div></section>
  </div></section>
}
