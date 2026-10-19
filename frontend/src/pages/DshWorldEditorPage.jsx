import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import {
  deleteResource, draftDownloadUrl, getResource, getResourceData, importDshWorld,
  listResourceVersions, publishResource, updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { CoAuthorEditor } from '../components/CoAuthorEditor.jsx'
import { TagEditor } from '../components/TagEditor.jsx'

export function DshWorldEditorPage() {
  const { resourceId } = useParams(); const location = useLocation(); const { t } = useTranslation()
  const { user, isLoading: authLoading } = useAuth(); const fileInput = useRef(null)
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [metadata, setMetadata] = useState(null); const [draft, setDraft] = useState(null)
  const [versions, setVersions] = useState([]); const [releaseVersion, setReleaseVersion] = useState('v1.0.0')
  const [busy, setBusy] = useState('load'); const [message, setMessage] = useState(''); const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    let active = true
    Promise.all([getResource(resourceId), listResourceVersions(resourceId)]).then(async ([loaded, releases]) => {
      if (loaded.resourceType !== 'dsh-agentic-roleplay/world') throw new Error('wrong type')
      if (!active) return
      setResource(loaded); setMetadata({ ...loaded.metadata, tags: [...loaded.metadata.tags] }); setVersions(releases)
      try { const document = await getResourceData(resourceId); if (active) setDraft(document) }
      catch (requestError) { if (requestError.status !== 404) throw requestError }
    }).catch(() => active && setError(t('dshWorld.loadFailed'))).finally(() => active && setBusy(''))
    return () => { active = false }
  }, [resourceId, t, user])

  if (!authLoading && !user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (authLoading || busy === 'load') return <div className="page-loading" role="status">{t('dshWorld.loading')}</div>
  if (!resource || !metadata) return <div className="page-loading error" role="alert">{error || t('dshWorld.loadFailed')}</div>
  const isOwner = user.id === resource.authorId

  async function saveMetadata() {
    const saved = await updateResource(resourceId, metadata, resource.revision)
    setResource(saved); setMetadata({ ...saved.metadata, tags: [...saved.metadata.tags] })
  }
  async function save() {
    setBusy('save'); setError(''); setMessage('')
    try { await saveMetadata(); setMessage(t('dshWorld.saved')) }
    catch { setError(t('dshWorld.saveFailed')) } finally { setBusy('') }
  }
  async function upload(file) {
    if (!file) return
    setBusy('import'); setError(''); setMessage('')
    try {
      const result = await importDshWorld(resourceId, file)
      setResource(result.resource); setDraft(result.draft); setMessage(t('dshWorld.imported'))
    } catch (requestError) { setError(requestError.message || t('dshWorld.importFailed')) }
    finally { setBusy(''); fileInput.current.value = '' }
  }
  async function publish() {
    if (!draft) { setError(t('dshWorld.uploadRequired')); return }
    setBusy('publish'); setError(''); setMessage('')
    try { await saveMetadata(); const version = await publishResource(resourceId, releaseVersion); setVersions((items) => [version, ...items]); setMessage(t('dshWorld.published')) }
    catch { setError(t('dshWorld.publishFailed')) } finally { setBusy('') }
  }
  function usePackageMetadata() {
    if (!draft) return
    setMetadata({
      ...metadata,
      name: draft.data.worldName,
      description: draft.data.description || metadata.description,
      tags: [...new Set([...metadata.tags, ...draft.data.tags])],
    })
    setMessage(t('dshWorld.metadataApplied'))
  }

  return <section className="character-editor-page"><div className="character-editor">
    <header className="editor-toolbar"><div><span className="eyebrow">{t('dshWorld.draft')}</span><h1>{metadata.name}</h1></div><div className="editor-actions">
      {isOwner && <button className="danger-button" type="button" onClick={async () => { if (confirm(t('editor.deleteConfirm'))) { await deleteResource(resourceId, resource.resourceType); window.location.assign('/resources/mine') } }}>{t('editor.delete')}</button>}
      <button type="button" onClick={() => fileInput.current?.click()}>{draft ? t('dshWorld.replaceZip') : t('dshWorld.uploadZip')}</button>
      {draft && <a className="editor-action-link" href={draftDownloadUrl(resourceId)}>{t('editor.export')}</a>}
      <button className="save-button" type="button" disabled={Boolean(busy)} onClick={save}>{busy === 'save' ? t('editor.saving') : t('editor.save')}</button>
    </div></header>
    <input hidden ref={fileInput} type="file" accept=".zip,application/zip" onChange={(event) => upload(event.target.files?.[0])} />
    {error && <p className="editor-message error" role="alert">{error}</p>}{message && <p className="editor-message success" role="status">{message}</p>}
    <section className="resource-metadata-editor"><h2>{t('editor.resourceMetadata')}</h2><div className="editor-field-grid">
      <label>{t('resource.name')}<input value={metadata.name} onChange={(event) => setMetadata({ ...metadata, name: event.target.value })} /></label>
      <label>{t('resource.visibility')}<select value={metadata.visibility} onChange={(event) => setMetadata({ ...metadata, visibility: event.target.value })}>{['private', 'authenticated', 'public'].map((item) => <option key={item} value={item}>{t(`resource.visibilities.${item}`)}</option>)}</select></label>
      <label>{t('resource.language')}<select value={metadata.language} onChange={(event) => setMetadata({ ...metadata, language: event.target.value })}><option value="en-uk">{t('resource.languages.enUK')}</option><option value="zh-cn">{t('resource.languages.zhCN')}</option></select></label>
      <label className="wide-field">{t('resource.description')}<textarea rows={3} value={metadata.description} onChange={(event) => setMetadata({ ...metadata, description: event.target.value })} /></label>
      <div className="wide-field"><label>{t('resource.tags')}</label><TagEditor value={metadata.tags} onChange={(tags) => setMetadata({ ...metadata, tags })} /></div>
    </div><CoAuthorEditor resourceId={resource.id} authorId={resource.authorId} currentUserId={user.id} /></section>
    <section className="preset-settings"><div className="section-heading"><div><h2>{t('dshWorld.package')}</h2><p>{t('dshWorld.packageHelp')}</p></div>{draft && <button type="button" onClick={usePackageMetadata}>{t('dshWorld.useMetadata')}</button>}</div>
      {draft ? <div className="world-count-grid"><div><strong>{draft.data.worldName}</strong><span>{t('dshWorld.worldName')}</span></div><div><strong>{draft.data.files.length}</strong><span>{t('dshWorld.files')}</span></div><div><strong>{(draft.data.byteSize / 1048576).toFixed(1)} MB</strong><span>{t('dshWorld.zipSize')}</span></div><div><strong>{draft.data.worldVersion || '—'}</strong><span>{t('dshWorld.worldVersion')}</span></div><div><strong>{draft.data.folderName}</strong><span>{t('dshWorld.folderName')}</span></div><div><strong>{draft.data.authorName || '—'}</strong><span>{t('dshWorld.packageAuthor')}</span></div></div>
        : <div className="catalogue-message empty"><h2>{t('dshWorld.noPackage')}</h2><p>{t('dshWorld.noPackageHelp')}</p><button type="button" onClick={() => fileInput.current?.click()}>{t('dshWorld.uploadZip')}</button></div>}
    </section>
    <section className="release-history"><h2>{t('editor.releases')}</h2>
      {isOwner && <div className="world-publish-row"><input value={releaseVersion} onChange={(event) => setReleaseVersion(event.target.value)} /><button className="save-button" disabled={Boolean(busy) || !draft} type="button" onClick={publish}>{t('editor.publish')}</button></div>}
      {versions.length ? <div className="release-grid">{versions.map((version) => <div className="release-tile" key={version.id}><strong>{version.version}</strong></div>)}</div> : <p>{t('editor.noReleases')}</p>}
    </section>
  </div></section>
}
