import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import { confirmPasswordReset, requestPasswordReset } from '../api/auth.js'

export function LoginPage() {
  const { t } = useTranslation()
  const { user, isLoading, login } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [resetMode, setResetMode] = useState('login')
  const [resetEmail, setResetEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [resetRequested, setResetRequested] = useState(false)
  const destination = location.state?.from && location.state.from !== '/login'
    ? location.state.from
    : '/'
  const activation = searchParams.get('activation')
  const resetUserId = searchParams.get('userId')
  const resetToken = searchParams.get('token')
  const isResetConfirmation = Boolean(resetUserId && resetToken)
  const activeMode = isResetConfirmation ? 'confirm' : resetMode

  useEffect(() => {
    const pageTitle = activeMode === 'request' ? t('auth.forgotPassword')
      : activeMode === 'confirm' ? t('auth.chooseNewPassword') : t('auth.login')
    document.title = `${pageTitle} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [activeMode, t])

  if (!isLoading && user) return <Navigate to={destination} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(username, password)
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(requestError.status === 401
        ? t('auth.invalidCredentials')
        : t('auth.loginFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function submitResetRequest(event) {
    event.preventDefault(); setError(''); setIsSubmitting(true)
    try {
      await requestPasswordReset(resetEmail)
      setResetRequested(true)
    } catch { setError(t('auth.resetRequestFailed')) }
    finally { setIsSubmitting(false) }
  }

  async function submitResetConfirmation(event) {
    event.preventDefault(); setError('')
    if (newPassword !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }
    setIsSubmitting(true)
    try {
      await confirmPasswordReset(resetUserId, resetToken, newPassword)
      navigate('/login?reset=success', { replace: true })
      setResetMode('login'); setNewPassword(''); setConfirmPassword('')
    } catch (requestError) {
      setError(requestError.status === 400 ? t('auth.resetInvalid') : t('auth.resetFailed'))
    } finally { setIsSubmitting(false) }
  }

  if (activeMode === 'request') {
    return (
      <section className="login-page"><div className="login-card">
        <div className="login-heading"><span className="eyebrow">{t('auth.accountRecovery')}</span>
          <h1>{t('auth.forgotPassword')}</h1><p>{t('auth.resetRequestDescription')}</p></div>
        {resetRequested ? <p className="form-notice success" role="status">{t('auth.resetRequested')}</p> : (
          <form onSubmit={submitResetRequest}>
            <label htmlFor="reset-email">{t('auth.email')}</label>
            <input id="reset-email" type="email" autoComplete="email" value={resetEmail}
              onChange={(event) => setResetEmail(event.target.value)} required autoFocus />
            {error && <p className="form-error" role="alert">{error}</p>}
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? t('auth.sendingReset') : t('auth.sendReset')}
            </button>
          </form>
        )}
        <button className="auth-text-button" type="button" onClick={() => {
          setResetMode('login'); setResetRequested(false); setError('')
        }}>{t('auth.backToLogin')}</button>
      </div></section>
    )
  }

  if (activeMode === 'confirm') {
    return (
      <section className="login-page"><div className="login-card">
        <div className="login-heading"><span className="eyebrow">{t('auth.accountRecovery')}</span>
          <h1>{t('auth.chooseNewPassword')}</h1><p>{t('auth.resetConfirmDescription')}</p></div>
        <form onSubmit={submitResetConfirmation}>
          <label htmlFor="new-password">{t('auth.newPassword')}</label>
          <input id="new-password" type="password" autoComplete="new-password" minLength={8}
            value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required autoFocus />
          <label htmlFor="confirm-password">{t('auth.confirmPassword')}</label>
          <input id="confirm-password" type="password" autoComplete="new-password" minLength={8}
            value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? t('auth.resettingPassword') : t('auth.resetPassword')}
          </button>
        </form>
        <button className="auth-text-button" type="button"
          onClick={() => navigate('/login', { replace: true })}>{t('auth.backToLogin')}</button>
      </div></section>
    )
  }

  return (
    <section className="login-page">
      <div className="login-card">
        <div className="login-heading">
          <span className="eyebrow">{t('auth.welcomeBack')}</span>
          <h1>{t('auth.loginTitle')}</h1>
          <p>{t('auth.loginDescription')}</p>
        </div>
        {activation === 'success' && (
          <p className="form-notice success" role="status">{t('auth.activationSuccess')}</p>
        )}
        {activation === 'invalid' && (
          <p className="form-notice error" role="alert">{t('auth.activationInvalid')}</p>
        )}
        {searchParams.get('reset') === 'success' && (
          <p className="form-notice success" role="status">{t('auth.resetSuccess')}</p>
        )}
        <form onSubmit={handleSubmit}>
          <label htmlFor="username">{t('auth.username')}</label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoFocus
          />
          <label htmlFor="password">{t('auth.password')}</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? t('auth.loggingIn') : t('auth.login')}
          </button>
        </form>
        <button className="auth-text-button" type="button" onClick={() => {
          setResetMode('request'); setError('')
        }}>{t('auth.forgotPassword')}</button>
        <p className="auth-switch">
          {t('auth.noAccount')}{' '}
          <Link to="/register" state={{ from: destination }}>{t('auth.createAccount')}</Link>
        </p>
      </div>
    </section>
  )
}
