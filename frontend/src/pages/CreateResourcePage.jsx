import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { createResource } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'

const RESOURCE_TYPES = [
  'sillytavern/character',
  'sillytavern/lorebook',
  'core/image',
]

const VISIBILITIES = ['private', 'authenticated', 'public']

export function CreateResourcePage() {
  const { t } = useTranslation()
  const { user, isLoading } = useAuth()
  const location = useLocation()
  const [resourceType, setResourceType] = useState(RESOURCE_TYPES[0])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [visibility, setVisibility] = useState(VISIBILITIES[0])
  const [tags, setTags] = useState('')
  const [createdResource, setCreatedResource] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    document.title = `${t('resource.createTitle')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [t])

  if (isLoading) {
    return <div className="page-loading" role="status">{t('auth.checkingSession')}</div>
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: `${location.pathname}${location.search}` }} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const resource = await createResource({
        resourceType,
        name,
        description,
        visibility,
        tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean),
      })
      setCreatedResource(resource)
    } catch (requestError) {
      setError(requestError.status === 401
        ? t('resource.sessionExpired')
        : t('resource.createFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  function createAnother() {
    setName('')
    setDescription('')
    setTags('')
    setCreatedResource(null)
  }

  return (
    <section className="create-resource-page">
      <div className="resource-form-card">
        {createdResource ? (
          <div className="resource-created" role="status">
            <span className="eyebrow">{t('resource.createdLabel')}</span>
            <h1>{t('resource.createdTitle')}</h1>
            <p>{t('resource.createdDescription', { name: createdResource.metadata.name })}</p>
            <dl>
              <div><dt>{t('resource.name')}</dt><dd>{createdResource.metadata.name}</dd></div>
              <div><dt>{t('resource.type')}</dt><dd>{t(`resource.types.${createdResource.resourceType}`)}</dd></div>
              <div><dt>{t('resource.resourceId')}</dt><dd><code>{createdResource.id}</code></dd></div>
            </dl>
            <div className="completion-actions">
              <button className="primary-button" type="button" onClick={createAnother}>
                {t('resource.createAnother')}
              </button>
              <Link to="/">{t('nav.home')}</Link>
            </div>
          </div>
        ) : (
          <>
            <div className="resource-form-heading">
              <span className="eyebrow">{t('resource.newLabel')}</span>
              <h1>{t('resource.createTitle')}</h1>
              <p>{t('resource.createDescription')}</p>
            </div>
            <form onSubmit={handleSubmit}>
              <label htmlFor="resource-name">{t('resource.name')}</label>
              <input
                id="resource-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={200}
                required
                autoFocus
              />

              <label htmlFor="resource-type">{t('resource.type')}</label>
              <select
                id="resource-type"
                value={resourceType}
                onChange={(event) => setResourceType(event.target.value)}
              >
                {RESOURCE_TYPES.map((type) => (
                  <option key={type} value={type}>{t(`resource.types.${type}`)}</option>
                ))}
              </select>
              <p className="field-help">{t(`resource.typeHelp.${resourceType}`)}</p>

              <label htmlFor="resource-description">{t('resource.description')}</label>
              <textarea
                id="resource-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={10000}
                rows={5}
              />

              <label htmlFor="resource-visibility">{t('resource.visibility')}</label>
              <select
                id="resource-visibility"
                value={visibility}
                onChange={(event) => setVisibility(event.target.value)}
              >
                {VISIBILITIES.map((value) => (
                  <option key={value} value={value}>{t(`resource.visibilities.${value}`)}</option>
                ))}
              </select>
              <p className="field-help">{t(`resource.visibilityHelp.${visibility}`)}</p>

              <label htmlFor="resource-tags">{t('resource.tags')}</label>
              <input
                id="resource-tags"
                value={tags}
                onChange={(event) => setTags(event.target.value)}
                placeholder={t('resource.tagsPlaceholder')}
              />
              <p className="field-help">{t('resource.tagsHelp')}</p>

              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? t('resource.creating') : t('resource.create')}
              </button>
            </form>
          </>
        )}
      </div>
    </section>
  )
}
