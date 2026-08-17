import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { changePassword, createApiKey, listApiKeys, revokeApiKey } from '../api/auth.js'
import { useAuth } from '../auth/useAuth.js'
import { CHINESE, ENGLISH, changeLocale, getCurrentLocale } from '../i18n.js'

export function ProfilePage() {
  const { t } = useTranslation()
  const { user, isLoading, deleteAccount } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [locale, setLocale] = useState(getCurrentLocale)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [apiKeys, setApiKeys] = useState([])
  const [apiKeyName, setApiKeyName] = useState('')
  const [apiKeyLifetime, setApiKeyLifetime] = useState('oneMonth')
  const [createdApiKey, setCreatedApiKey] = useState(null)
  const [apiKeyError, setApiKeyError] = useState('')
  const [isLoadingApiKeys, setIsLoadingApiKeys] = useState(false)
  const [isCreatingApiKey, setIsCreatingApiKey] = useState(false)
  const [revokingApiKeyId, setRevokingApiKeyId] = useState(null)
  const [keyCopied, setKeyCopied] = useState(false)

  useEffect(() => {
    document.title = `${t('profile.title')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [t])

  useEffect(() => {
    if (!isDeleteOpen) return undefined
    const closeOnEscape = (event) => {
      if (event.key === 'Escape' && !isDeleting) setIsDeleteOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [isDeleteOpen, isDeleting])

  useEffect(() => {
    if (!user) return
    let active = true
    setIsLoadingApiKeys(true)
    listApiKeys()
      .then((keys) => { if (active) setApiKeys(keys) })
      .catch(() => { if (active) setApiKeyError(t('profile.apiKeysLoadFailed')) })
      .finally(() => { if (active) setIsLoadingApiKeys(false) })
    return () => { active = false }
  }, [user, t])

  if (isLoading) return <div className="page-loading" role="status">{t('auth.checkingSession')}</div>
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />

  async function submitPasswordChange(event) {
    event.preventDefault()
    setPasswordError(''); setPasswordMessage('')
    if (newPassword !== confirmPassword) {
      setPasswordError(t('profile.passwordMismatch'))
      return
    }
    setIsChangingPassword(true)
    try {
      await changePassword(currentPassword, newPassword)
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
      setPasswordMessage(t('profile.passwordChanged'))
    } catch (error) {
      setPasswordError(error.status === 401
        ? t('profile.currentPasswordIncorrect') : t('profile.passwordChangeFailed'))
    } finally { setIsChangingPassword(false) }
  }

  async function confirmDelete(event) {
    event.preventDefault()
    setDeleteError(''); setIsDeleting(true)
    try {
      await deleteAccount(deletePassword)
      navigate('/', { replace: true })
    } catch (error) {
      setDeleteError(error.status === 401
        ? t('profile.currentPasswordIncorrect') : t('profile.deleteFailed'))
    } finally { setIsDeleting(false) }
  }

  function selectLocale(event) {
    const selected = event.target.value
    setLocale(selected)
    changeLocale(selected)
  }

  async function submitApiKey(event) {
    event.preventDefault()
    setApiKeyError(''); setCreatedApiKey(null); setKeyCopied(false); setIsCreatingApiKey(true)
    try {
      const created = await createApiKey(apiKeyName, apiKeyLifetime)
      const metadata = {
        id: created.id, name: created.name,
        createdAt: created.createdAt, expiresAt: created.expiresAt,
      }
      setApiKeys((current) => [metadata, ...current])
      setCreatedApiKey({ ...created, displayValue: `${created.id}:${created.key}` })
      setApiKeyName('')
    } catch {
      setApiKeyError(t('profile.apiKeyCreateFailed'))
    } finally { setIsCreatingApiKey(false) }
  }

  async function revokeKey(keyId) {
    setApiKeyError(''); setRevokingApiKeyId(keyId)
    try {
      await revokeApiKey(keyId)
      setApiKeys((current) => current.filter((key) => key.id !== keyId))
      if (createdApiKey?.id === keyId) setCreatedApiKey(null)
    } catch {
      setApiKeyError(t('profile.apiKeyRevokeFailed'))
    } finally { setRevokingApiKeyId(null) }
  }

  async function copyCreatedKey() {
    try {
      await navigator.clipboard.writeText(createdApiKey.displayValue)
      setKeyCopied(true)
    } catch { setApiKeyError(t('profile.apiKeyCopyFailed')) }
  }

  function formatDate(value) {
    return new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(new Date(value))
  }

  return (
    <section className="profile-page" aria-labelledby="profile-heading">
      <div className="profile-heading">
        <span className="eyebrow">{t('profile.account')}</span>
        <h1 id="profile-heading">{t('profile.title')}</h1>
        <p>{t('profile.description', { username: user.username })}</p>
      </div>

      <section className="profile-card">
        <div><h2>{t('profile.language')}</h2><p>{t('profile.languageHelp')}</p></div>
        <label>{t('profile.locale')}
          <select value={locale} onChange={selectLocale}>
            <option value={ENGLISH}>{t('profile.locales.enUK')}</option>
            <option value={CHINESE}>{t('profile.locales.zhCN')}</option>
          </select>
        </label>
      </section>

      <section className="profile-card">
        <div><h2>{t('profile.changePassword')}</h2><p>{t('profile.changePasswordHelp')}</p></div>
        <form onSubmit={submitPasswordChange}>
          <label>{t('profile.currentPassword')}<input type="password" autoComplete="current-password"
            value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          <label>{t('profile.newPassword')}<input type="password" autoComplete="new-password" minLength={8}
            value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          <label>{t('profile.confirmPassword')}<input type="password" autoComplete="new-password" minLength={8}
            value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></label>
          {passwordError && <p className="form-error" role="alert">{passwordError}</p>}
          {passwordMessage && <p className="form-notice success" role="status">{passwordMessage}</p>}
          <button className="primary-button" type="submit" disabled={isChangingPassword}>
            {isChangingPassword ? t('profile.changingPassword') : t('profile.changePassword')}
          </button>
        </form>
      </section>

      <section className="profile-card api-key-card">
        <div><h2>{t('profile.apiKeys')}</h2><p>{t('profile.apiKeysHelp')}</p></div>
        <div className="api-key-controls">
          <form onSubmit={submitApiKey}>
            <label>{t('profile.apiKeyName')}<input value={apiKeyName} maxLength={100}
              onChange={(event) => setApiKeyName(event.target.value)} required /></label>
            <label>{t('profile.apiKeyExpiration')}
              <select value={apiKeyLifetime} onChange={(event) => setApiKeyLifetime(event.target.value)}>
                <option value="oneWeek">{t('profile.apiKeyLifetimes.oneWeek')}</option>
                <option value="oneMonth">{t('profile.apiKeyLifetimes.oneMonth')}</option>
                <option value="sixMonths">{t('profile.apiKeyLifetimes.sixMonths')}</option>
                <option value="oneYear">{t('profile.apiKeyLifetimes.oneYear')}</option>
                <option value="never">{t('profile.apiKeyLifetimes.never')}</option>
              </select>
            </label>
            <button className="primary-button" disabled={isCreatingApiKey}>
              {isCreatingApiKey ? t('profile.creatingApiKey') : t('profile.createApiKey')}
            </button>
          </form>
          {createdApiKey && <div className="api-key-reveal" role="status">
            <strong>{t('profile.apiKeyCreated')}</strong>
            <p>{t('profile.apiKeyShownOnce')}</p>
            <code>{createdApiKey.displayValue}</code>
            <button type="button" onClick={copyCreatedKey}>
              {keyCopied ? t('profile.apiKeyCopied') : t('profile.copyApiKey')}
            </button>
          </div>}
          {apiKeyError && <p className="form-error" role="alert">{apiKeyError}</p>}
          <div className="api-key-list">
            <h3>{t('profile.existingApiKeys')}</h3>
            {isLoadingApiKeys ? <p>{t('profile.loadingApiKeys')}</p> : apiKeys.length === 0
              ? <p>{t('profile.noApiKeys')}</p>
              : apiKeys.map((key) => <div className="api-key-row" key={key.id}>
                <div><strong>{key.name}</strong><small>
                  {key.expiresAt ? t('profile.apiKeyExpires', { date: formatDate(key.expiresAt) })
                    : t('profile.apiKeyNeverExpires')}
                </small></div>
                <button className="danger-action" type="button" disabled={revokingApiKeyId === key.id}
                  onClick={() => revokeKey(key.id)}>
                  {revokingApiKeyId === key.id ? t('profile.revokingApiKey') : t('profile.revokeApiKey')}
                </button>
              </div>)}
          </div>
        </div>
      </section>

      <section className="profile-card danger-zone">
        <div><h2>{t('profile.deleteAccount')}</h2><p>{t('profile.deleteAccountHelp')}</p></div>
        <button className="danger-action" type="button" onClick={() => setIsDeleteOpen(true)}>
          {t('profile.deleteAccount')}
        </button>
      </section>

      {isDeleteOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !isDeleting) setIsDeleteOpen(false)
        }}>
          <div className="delete-account-dialog" role="dialog" aria-modal="true"
            aria-labelledby="delete-account-heading">
            <span className="danger-symbol" aria-hidden="true">!</span>
            <h2 id="delete-account-heading">{t('profile.deleteWarningTitle')}</h2>
            <p>{t('profile.deleteWarning')}</p>
            <ul>
              <li>{t('profile.deleteResources')}</li>
              <li>{t('profile.deleteReleases')}</li>
              <li>{t('profile.deleteImages')}</li>
              <li>{t('profile.deleteIrreversible')}</li>
            </ul>
            <form onSubmit={confirmDelete}>
              <label>{t('profile.confirmWithPassword')}<input autoFocus type="password"
                autoComplete="current-password" value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)} required /></label>
              {deleteError && <p className="form-error" role="alert">{deleteError}</p>}
              <div className="modal-actions">
                <button type="button" disabled={isDeleting} onClick={() => setIsDeleteOpen(false)}>
                  {t('profile.cancel')}
                </button>
                <button className="confirm-delete-button" type="submit" disabled={isDeleting}>
                  {isDeleting ? t('profile.deleting') : t('profile.deletePermanently')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  )
}
