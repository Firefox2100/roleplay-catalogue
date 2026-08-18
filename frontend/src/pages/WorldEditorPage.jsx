import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import {
  deleteResource, draftDownloadUrl, getResource, getResourceData, importWorldBundle,
  imageContentUrl, listResourceVersions, publishResource, saveResourceData, updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { TagEditor } from '../components/TagEditor.jsx'

const SECTION_TEMPLATES = {
  locations: () => ({ id: crypto.randomUUID(), name: '', description: '', parent_location_id: null }),
  landmarks: () => ({ id: crypto.randomUUID(), name: '', description: '', location_id: null, cover_media_id: null }),
  characters: () => ({ id: crypto.randomUUID(), user_controlled: false, name: '', age: 18, gender: '', appearance: '', description: '', public_state: '', private_state: '', current_activity: { name: 'idle', started_at: null, expected_end: null, interruptible: true, constraints: [] }, speech_style: '', location_id: null, position: null, landmark_id: null, cover_media_id: null }),
  background_characters: () => ({ id: crypto.randomUUID(), name: '', description: '', location_id: null, position: null, landmark_id: null, cover_media_id: null }),
  items: () => ({ id: crypto.randomUUID(), name: '', description: '', unique: false, cover_media_id: null }),
  item_stacks: () => ({ id: crypto.randomUUID(), quantity: 1, quality: null, item_id: null, owner_id: null, holder_id: null, location_id: null, position: null }),
  equipment: () => ({ id: crypto.randomUUID(), name: '', description: '', quality: null, owner_id: null, holder_id: null, location_id: null, position: null, equipped: false, equipped_position: null, cover_media_id: null }),
  containers: () => ({ id: crypto.randomUUID(), name: '', description: '', state: 'unlocked', owner_id: null, holder_id: null, location_id: null, position: null, held_stack_ids: [], held_equipment_ids: [], held_container_ids: [], unlocking_item_ids: [], cover_media_id: null }),
  turns: () => ({ id: crypto.randomUUID(), sequence: 1, type: 'system_response', content: '', start_time: new Date().toISOString() }),
  events: () => ({ id: crypto.randomUUID(), name: '', summary: '', outcome: null, turn_ids: [], involved_characters: [] }),
  memories: () => ({ id: crypto.randomUUID(), summary: '', keywords: [], embedding: null, event_id: null, support_type: 'direct', character_links: [] }),
  intents: () => ({ id: crypto.randomUUID(), type: 'quest', name: '', description: '', keywords: [], embedding: null, priority: 0.5, urgency: 0.5, status: 'active', desired_state: null, success_conditions: [], failure_conditions: [], maintenance_conditions: [], deadline: null, horizon: 'short', constraints: [], current_plan: [], next_action_biases: [], blockers: [], open_threads: [], character_id: null, created_by_event_id: null, contributed_by_event_ids: [] }),
  entity_relationships: () => ({ id: crypto.randomUUID(), scope_type: 'world', scope_id: null, source: { type: 'character', id: '', name: null }, target: { type: 'character', id: '', name: null }, label: '', public_description: null, private_description: null, visibility: 'objective', perspective_character_id: null, confidence: 1, details: { kind: 'generic', attributes: {} }, evidence_memory_ids: [], created_at: new Date().toISOString(), last_changed_at: new Date().toISOString(), version: 1, active: true }),
  subjective_entity_claims: () => ({ id: crypto.randomUUID(), simulation_id: null, world_id: null, observer_character_id: null, subject: { type: 'character', id: '', name: null }, category: 'other', statement: '', normalized_statement: '', stance: 'believes', confidence: 1, supporting_memory_ids: [], contradicting_memory_ids: [], first_observed_at: new Date().toISOString(), last_updated_at: new Date().toISOString(), version: 1, active: true }),
  entity_variable_sets: () => ({ id: crypto.randomUUID(), source_id: null, owner_type: 'character', owner_id: null, variables: [], last_updated_at: new Date().toISOString(), version: 1 }),
}

const REFERENCE_TARGETS = {
  parent_location_id: 'locations', location_id: 'locations', landmark_id: 'landmarks',
  item_id: 'items', unlocking_item_ids: 'items', held_stack_ids: 'item_stacks',
  held_equipment_ids: 'equipment', held_container_ids: 'containers', turn_ids: 'turns',
  event_id: 'events', created_by_event_id: 'events', contributed_by_event_ids: 'events',
  character_id: 'characters', observer_character_id: 'characters', perspective_character_id: 'characters',
  evidence_memory_ids: 'memories', supporting_memory_ids: 'memories', contradicting_memory_ids: 'memories',
}
const ENUMS = {
  language: ['en', 'zh'], state: ['hidden', 'locked', 'unlocked', 'open'],
  type: [], visibility: ['public', 'private', 'objective'],
  support_type: ['direct', 'inferred', 'reported', 'contradicts'],
  horizon: ['immediate', 'short', 'day', 'long', 'open_ended'],
  status: ['active', 'paused', 'completed', 'failed', 'abandoned'],
}
const LONG_FIELDS = new Set(['description', 'appearance', 'public_state', 'private_state', 'content', 'summary', 'outcome', 'comment', 'speech_style', 'statement', 'normalized_statement', 'public_description', 'private_description'])
const INTERNAL_FIELDS = new Set(['id', 'scope_id', 'world_id', 'source_id', 'simulation_id', 'cover_media_id'])
const STRUCTURED_ARRAY_FIELDS = new Set(['involved_characters', 'character_links', 'variables'])

function emptyWorld(name, description) {
  const id = crypto.randomUUID()
  return {
    spec: 'wse_world', specVersion: '1.0',
    world: { id, name, description, starting_time: new Date().toISOString(), version: 1, url: null, language: 'en', metadata: { author: null, author_url: null, resource_url: null, comment: null, version: null }, creation_time: new Date().toISOString(), cover_media_id: null },
    author: null,
    sections: Object.fromEntries(Object.keys(SECTION_TEMPLATES).map((key) => [key, []])),
    configs: { chat: [], embed: [], image: [], tts: [] }, prompts: [], workflows: [], media: [],
  }
}

function displayName(row, fallback) {
  return row.name || row.title || row.summary || `${fallback}`
}

function JsonField({ value, onChange }) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2))
  useEffect(() => setText(JSON.stringify(value, null, 2)), [value])
  function commit() {
    try { onChange(JSON.parse(text)) } catch { /* keep invalid text available for correction */ }
  }
  return <textarea className="world-json-field" rows={5} value={text}
    onChange={(event) => setText(event.target.value)} onBlur={commit} />
}

function WorldField({ field, value, onChange, registry, section, t }) {
  const label = t(`world.fields.${field}`, { defaultValue: field.replaceAll('_', ' ') })
  if (['source', 'target', 'subject'].includes(field) && value && typeof value === 'object') {
    return <label>{label}<select value={value.id ?? ''} onChange={(event) => {
      const selected = registry.allPhysical.find((option) => option.id === event.target.value)
      onChange(selected ? { ...value, id: selected.id, name: selected.label, type: selected.type } : { ...value, id: '', name: null })
    }}><option value="">—</option>{registry.allPhysical.map((option) => <option key={`${option.type}:${option.id}`} value={option.id}>{option.label}</option>)}</select></label>
  }
  const target = REFERENCE_TARGETS[field]
  const genericEntityReference = ['owner_id', 'holder_id', 'owner_id'].includes(field)
  const options = target ? registry[target] : genericEntityReference ? registry.allPhysical : null
  if (options && Array.isArray(value)) {
    return <label>{label}<select multiple value={value} onChange={(event) => onChange(
      [...event.target.selectedOptions].map((option) => option.value),
    )}>{options.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
  }
  if (options) {
    return <label>{label}<select value={value ?? ''} onChange={(event) => onChange(event.target.value || null)}>
      <option value="">—</option>{options.filter((option) => option.id !== (section === target ? value : null)).map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
    </select></label>
  }
  if (typeof value === 'boolean') return <label className="checkbox-field"><input type="checkbox" checked={value} onChange={(event) => onChange(event.target.checked)} />{label}</label>
  if (typeof value === 'number') return <label>{label}<input type="number" step="any" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>
  if (Array.isArray(value) && !STRUCTURED_ARRAY_FIELDS.has(field) && value.every((item) => ['string', 'number'].includes(typeof item))) {
    return <label>{label}<input value={value.join(', ')} onChange={(event) => onChange(event.target.value.split(',').map((item) => item.trim()).filter(Boolean))} /></label>
  }
  if (value !== null && typeof value === 'object') return <label className="wide-field">{label}<JsonField value={value} onChange={onChange} /></label>
  const enumValues = field === 'type' ? (section === 'turns' ? ['user_input', 'system_response', 'system_continue'] : section === 'intents' ? ['need', 'obligation', 'quest', 'agenda', 'aspiration', 'relationship', 'habit', 'reaction'] : []) : ENUMS[field]
  if (enumValues?.length) return <label>{label}<select value={value ?? ''} onChange={(event) => onChange(event.target.value || null)}><option value="">—</option>{enumValues.map((option) => <option key={option}>{option}</option>)}</select></label>
  return <label className={LONG_FIELDS.has(field) ? 'wide-field' : ''}>{label}{LONG_FIELDS.has(field)
    ? <textarea rows={3} value={value ?? ''} onChange={(event) => onChange(event.target.value || null)} />
    : <input value={value ?? ''} onChange={(event) => onChange(event.target.value || null)} />}</label>
}

function EntitySection({ name, rows, onChange, registry, t, worldId }) {
  const [openRows, setOpenRows] = useState(new Set())
  function add() {
    const row = SECTION_TEMPLATES[name]()
    if ('scope_id' in row) row.scope_id = worldId
    if ('world_id' in row) row.world_id = worldId
    if ('source_id' in row) row.source_id = worldId
    onChange([...rows, row]); setOpenRows((current) => new Set(current).add(row.id))
  }
  function update(index, field, value) {
    const next = [...rows]; next[index] = { ...next[index], [field]: value }; onChange(next)
  }
  return <details className="world-section">
    <summary><span>{t(`world.sections.${name}`)}</span><small>{rows.length}</small></summary>
    <div className="world-section-body">
      {rows.map((row, index) => <article className="world-entity" key={row.id}>
        <button className="world-entity-heading" type="button" onClick={() => setOpenRows((current) => {
          const next = new Set(current); next.has(row.id) ? next.delete(row.id) : next.add(row.id); return next
        })}><strong>{displayName(row, `${t(`world.sections.${name}`)} ${index + 1}`)}</strong><span>{openRows.has(row.id) ? '−' : '+'}</span></button>
        {openRows.has(row.id) && <div className="world-entity-fields">
          {Object.entries(row).filter(([field]) => !INTERNAL_FIELDS.has(field)).map(([field, value]) => <WorldField
            key={field} field={field} value={value} section={name} registry={registry} t={t}
            onChange={(newValue) => update(index, field, newValue)} />)}
          <button className="danger-button world-remove" type="button" onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>{t('world.removeEntity')}</button>
        </div>}
      </article>)}
      <button className="add-list-button" type="button" onClick={add}>{t('world.addEntity')}</button>
    </div>
  </details>
}

export function WorldEditorPage() {
  const { resourceId } = useParams()
  const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth()
  const location = useLocation()
  const importInput = useRef(null)
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [bundle, setBundle] = useState(null)
  const [metadata, setMetadata] = useState(null)
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
        if (!active) return
        if (loaded.resourceType !== 'world-simulation-engine/world') throw new Error('wrong type')
        setResource(loaded); setMetadata({ ...loaded.metadata, tags: [...loaded.metadata.tags] }); setVersions(releases)
        try { const document = await getResourceData(resourceId); if (active) setBundle(document.data) }
        catch (requestError) { if (requestError.status === 404 && active) setBundle(emptyWorld(loaded.metadata.name, loaded.metadata.description)); else throw requestError }
      })
      .catch(() => { if (active) setError(t('world.loadFailed')) })
      .finally(() => { if (active) setBusy('') })
    return () => { active = false }
  }, [resourceId, user, t])

  const registry = useMemo(() => {
    const result = {}
    for (const [section, rows] of Object.entries(bundle?.sections ?? {})) result[section] = rows.map((row, index) => ({ id: row.id, label: displayName(row, `${section} ${index + 1}`), type: section === 'background_characters' ? 'background_character' : section.replace(/s$/, '') }))
    result.allPhysical = ['locations', 'landmarks', 'characters', 'background_characters', 'items', 'equipment', 'containers'].flatMap((section) => result[section] ?? [])
    return result
  }, [bundle])

  if (authLoading || busy === 'load') return <div className="page-loading">{t('world.loading')}</div>
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (!resource || !bundle || !metadata) return <div className="page-loading">{error || t('world.loadFailed')}</div>

  async function save() {
    setBusy('save'); setError(''); setMessage('')
    try {
      const nextBundle = { ...bundle, world: { ...bundle.world, name: metadata.name, description: metadata.description } }
      const [updated] = await Promise.all([updateResource(resourceId, metadata), saveResourceData(resourceId, nextBundle)])
      setResource(updated); setBundle(nextBundle); setMessage(t('world.saved'))
    } catch { setError(t('world.saveFailed')) } finally { setBusy('') }
  }
  async function importBundle(file) {
    if (!file) return
    setBusy('import'); setError(''); setMessage('')
    try { const result = await importWorldBundle(resourceId, file); setResource(result.resource); setBundle(result.draft.data); setMessage(t('world.imported')) }
    catch { setError(t('world.importFailed')) } finally { setBusy(''); importInput.current.value = '' }
  }
  async function publish() {
    setBusy('publish'); setError('')
    try {
      const nextBundle = { ...bundle, world: { ...bundle.world, name: metadata.name, description: metadata.description } }
      const [updated] = await Promise.all([updateResource(resourceId, metadata), saveResourceData(resourceId, nextBundle)])
      setResource(updated); setBundle(nextBundle)
      const version = await publishResource(resourceId, releaseVersion)
      setVersions((current) => [version, ...current]); setMessage(t('world.published'))
    }
    catch { setError(t('world.publishFailed')) } finally { setBusy('') }
  }

  return <section className="world-editor-page"><div className="world-editor">
    <header className="editor-toolbar"><div><span className="eyebrow">{t('world.model')}</span><h1>{metadata.name}</h1></div>
      <div className="editor-actions">
        <button className="danger-button" type="button" onClick={async () => { if (confirm(t('editor.deleteConfirm'))) { await deleteResource(resourceId, resource.resourceType); window.location.assign('/resources/mine') } }}>{t('editor.delete')}</button>
        <button type="button" onClick={() => importInput.current?.click()} disabled={Boolean(busy)}>{t('editor.upload')}</button>
        <a className="editor-action-link" href={draftDownloadUrl(resourceId)}>{t('editor.export')}</a>
        <button className="save-button" type="button" onClick={save} disabled={Boolean(busy)}>{busy === 'save' ? t('editor.saving') : t('editor.save')}</button>
      </div></header>
    <input ref={importInput} hidden type="file" accept=".zip,application/zip" onChange={(event) => importBundle(event.target.files?.[0])} />
    {error && <p className="editor-message error">{error}</p>}{message && <p className="editor-message success">{message}</p>}
    <section className="resource-metadata-editor"><div><h2>{t('editor.resourceMetadata')}</h2><p>{t('editor.resourceMetadataHelp')}</p></div>
      <div className="editor-field-grid"><label>{t('resource.name')}<input value={metadata.name} onChange={(event) => setMetadata({ ...metadata, name: event.target.value })} /></label>
        <label>{t('resource.visibility')}<select value={metadata.visibility} onChange={(event) => setMetadata({ ...metadata, visibility: event.target.value })}><option value="private">{t('resource.visibilities.private')}</option><option value="authenticated">{t('resource.visibilities.authenticated')}</option><option value="public">{t('resource.visibilities.public')}</option></select></label>
        <label className="wide-field">{t('resource.description')}<textarea rows={3} value={metadata.description} onChange={(event) => setMetadata({ ...metadata, description: event.target.value })} /></label>
        <div className="wide-field resource-tag-field"><label>{t('resource.tags')}</label><TagEditor value={metadata.tags} onChange={(tags) => setMetadata({ ...metadata, tags })} /></div></div>
    </section>
    <section className="world-settings"><h2>{t('world.settings')}</h2><div className="editor-field-grid">
      {Object.entries(bundle.world).filter(([field]) => !['id', 'creation_time', 'cover_media_id'].includes(field)).map(([field, value]) => <WorldField key={field} field={field} value={value} section="world" registry={registry} t={t} onChange={(newValue) => setBundle({ ...bundle, world: { ...bundle.world, [field]: newValue } })} />)}
    </div></section>
    <div className="world-graph-sections">{Object.keys(SECTION_TEMPLATES).map((name) => <EntitySection key={name} name={name} rows={bundle.sections[name] ?? []} registry={registry} t={t} worldId={bundle.world.id} onChange={(rows) => setBundle({ ...bundle, sections: { ...bundle.sections, [name]: rows } })} />)}</div>
    <section className="world-integrations"><h2>{t('world.integrations')}</h2><p>{t('world.integrationsHelp')}</p>
      <div className="world-integration-counts">
        {Object.entries(bundle.configs).map(([name, rows]) => <span key={name}><strong>{rows.length}</strong> {name}</span>)}
        <span><strong>{bundle.prompts.length}</strong> {t('world.prompts')}</span>
        <span><strong>{bundle.workflows.length}</strong> {t('world.workflows')}</span>
      </div>
      <div className="world-media-grid">{bundle.media.map((media, index) => <article key={media.mediaId}>
        {media.imageResourceId ? <img src={imageContentUrl(media.imageResourceId)} alt="" /> : <div className="world-media-placeholder">{t('world.unavailableMedia')}</div>}
        <strong>{media.record.title || media.record.name || `${t('world.media')} ${index + 1}`}</strong>
        <small>{media.record.type || t('world.unknownMedia')}</small>
      </article>)}</div>
    </section>
    <section className="release-history"><div className="section-heading"><div><h2>{t('editor.releases')}</h2><p>{t('editor.releasesHelp')}</p></div></div>
      <div className="world-publish-row"><input value={releaseVersion} onChange={(event) => setReleaseVersion(event.target.value)} /><button className="save-button" type="button" disabled={Boolean(busy) || !releaseVersion.trim()} onClick={publish}>{busy === 'publish' ? t('editor.publishing') : t('editor.publish')}</button></div>
      <div className="release-grid">{versions.map((version) => <div className="release-tile" key={version.id}><div><strong>{version.version}</strong><small>#{version.versionNumber}</small></div></div>)}</div>
    </section>
  </div></section>
}
