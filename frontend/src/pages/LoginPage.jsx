import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'

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
  const destination = location.state?.from && location.state.from !== '/login'
    ? location.state.from
    : '/'
  const activation = searchParams.get('activation')

  useEffect(() => {
    document.title = `${t('auth.login')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [t])

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
        <p className="auth-switch">
          {t('auth.noAccount')}{' '}
          <Link to="/register" state={{ from: destination }}>{t('auth.createAccount')}</Link>
        </p>
      </div>
    </section>
  )
}
