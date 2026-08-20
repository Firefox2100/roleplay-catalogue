import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  deleteResource, getResource, imageContentUrl, updateImageMetadata,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ResourceImage } from '../components/ResourceImage.jsx'
import { TagEditor } from '../components/TagEditor.jsx'
import { CoAuthorEditor } from '../components/CoAuthorEditor.jsx'
import { ConflictResolutionModal } from '../components/ConflictResolutionModal.jsx'
import { useConflictAwareSave } from '../hooks/useConflictAwareSave.js'
import { resourceToMetadataPayload } from '../utils/resourceMetadataPayload.js'

const VISIBILITIES = ['private', 'authenticated', 'public']

export function ImageEditorPage() {
  const { t } = useTranslation()
  const { resourceId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isLoading: isAuthLoading } = useAuth()
  const [resource, setResource] = useState(location.state?.resource ?? null)
  const [fields, setFields] = useState({
    name: '', description: '', language: 'en-uk', visibility: 'private', tags: [],
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return undefined
    let active = true
    const request = resource ? Promise.resolve(resource) : getResource(resourceId)
    request.then((loaded) => {
      if (!active) return
      if (loaded.resourceType !== 'core/image') throw new Error('Wrong resource type')
      setResource(loaded)
      setFields({
        name: loaded.metadata.name,
        description: loaded.metadata.description,
        language: loaded.metadata.language ?? 'en-uk',
        visibility: loaded.metadata.visibility,
        tags: loaded.metadata.tags ?? [],
      })
    }).catch(() => {
      if (active) setError(t('imageEditor.loadFailed'))
    }).finally(() => {
      if (active) setIsLoading(false)
    })
    return () => { active = false }
  }, [resource, resourceId, t, user])

  useEffect(() => {
    document.title = `${resource?.metadata.name ?? t('imageEditor.title')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [resource, t])

  const metadataSave = useConflictAwareSave({
    apiSave: (payload, revision) => updateImageMetadata(resourceId, payload, revision),
    extractComparable: resourceToMetadataPayload,
    extractRevision: (full) => full.revision,
    onSaved: (updatedResource) => {
      setResource(updatedResource)
      setFields({
        name: updatedResource.metadata.name,
        description: updatedResource.metadata.description,
        language: updatedResource.metadata.language ?? 'en-uk',
        visibility: updatedResource.metadata.visibility,
        tags: updatedResource.metadata.tags ?? [],
      })
    },
  })

  if (!isAuthLoading && !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  if (isAuthLoading || isLoading) {
    return <div className="page-loading" role="status">{t('imageEditor.loading')}</div>
  }

  const isOwner = user.id === resource.authorId

  async function save(event) {
    event.preventDefault()
    setIsSaving(true)
    setError('')
    setMessage('')
    try {
      const saved = await metadataSave.attempt(fields, resourceToMetadataPayload(resource), resource.revision)
      if (saved) setMessage(t('imageEditor.saved'))
    } catch (requestError) {
      setError(requestError.status === 422
        ? t('imageEditor.validationFailed')
        : t('imageEditor.saveFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  async function retryConflict(resolved) {
    setError('')
    try {
      if (await metadataSave.retry(resolved)) setMessage(t('imageEditor.saved'))
    } catch {
      setError(t('editor.conflictRetryFailed'))
    }
  }

  async function removeResource() {
    if (!window.confirm(t('editor.deleteImageConfirm'))) return
    try { await deleteResource(resourceId, resource.resourceType); navigate('/resources/mine', { replace: true }) }
    catch { setError(t('editor.deleteFailed')) }
  }

  return (
    <section className="image-editor-page">
      <form className="image-editor-card" onSubmit={save}>
        <div className="image-editor-heading">
          <div><span className="eyebrow">{t('imageEditor.immutableImage')}</span>
            <h1>{resource?.metadata.name}</h1></div>
          <button className="save-button" type="submit" disabled={isSaving}>
            {isSaving ? t('editor.saving') : t('editor.save')}
          </button>
          {isOwner && <button className="danger-button" type="button" onClick={removeResource}>{t('editor.delete')}</button>}
        </div>
        {error && <p className="editor-message error" role="alert">{error}</p>}
        {message && <p className="editor-message success" role="status">{message}</p>}
        <div className="image-editor-layout">
          <ResourceImage className="image-editor-preview" src={imageContentUrl(resourceId)} />
          <div className="image-metadata-form">
            <label>{t('resource.name')}<input value={fields.name} required maxLength={200}
              onChange={(event) => setFields((current) => ({
                ...current, name: event.target.value,
              }))} /></label>
            <label>{t('resource.description')}<textarea value={fields.description} rows={6}
              maxLength={10000} onChange={(event) => setFields((current) => ({
                ...current, description: event.target.value,
              }))} /></label>
            <label>{t('resource.visibility')}<select value={fields.visibility}
              onChange={(event) => setFields((current) => ({
                ...current, visibility: event.target.value,
              }))}>
              {VISIBILITIES.map((visibility) => (
                <option key={visibility} value={visibility}>
                  {t(`resource.visibilities.${visibility}`)}
                </option>
              ))}
            </select></label>
            <label>{t('resource.language')}<select value={fields.language}
              onChange={(event) => setFields((current) => ({ ...current, language: event.target.value }))}>
              <option value="en-uk">{t('resource.languages.enUK')}</option><option value="zh-cn">{t('resource.languages.zhCN')}</option>
            </select></label>
            <div><label htmlFor="image-editor-tags">{t('resource.tags')}</label>
              <TagEditor id="image-editor-tags" value={fields.tags}
                onChange={(tags) => setFields((current) => ({ ...current, tags }))} /></div>
            <CoAuthorEditor resourceId={resource.id} authorId={resource.authorId} currentUserId={user.id} />
          </div>
        </div>
      </form>
      {metadataSave.conflict && (
        <ConflictResolutionModal
          conflicts={metadataSave.conflict.conflicts}
          merged={metadataSave.conflict.merged}
          isRetrying={metadataSave.isRetrying}
          onApply={retryConflict}
          onCancel={metadataSave.cancel}
        />
      )}
    </section>
  )
}
