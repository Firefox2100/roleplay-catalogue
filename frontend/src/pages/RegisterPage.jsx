import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { register } from '../api/auth.js'
import { useAuth } from '../auth/useAuth.js'
import { passwordStrengthError } from '../utils/passwordStrength.js'

export function RegisterPage() {
  const { t } = useTranslation()
  const { user, isLoading } = useAuth()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRegistered, setIsRegistered] = useState(false)
  const destination = location.state?.from && location.state.from !== '/register'
    ? location.state.from
    : '/'

  useEffect(() => {
    document.title = `${t('auth.register')} · ${t('app.title')}`
    return () => { document.title = t('app.title') }
  }, [t])

  if (!isLoading && user) return <Navigate to={destination} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }
    const strengthError = passwordStrengthError(password)
    if (strengthError) {
      setError(t(`auth.passwordRules.${strengthError}`))
      return
    }
    setIsSubmitting(true)
    try {
      await register(username, email, password)
      setIsRegistered(true)
    } catch (requestError) {
      setError(requestError.status === 409
        ? t('auth.accountExists')
        : t('auth.registrationFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="login-page">
      <div className="login-card">
        {isRegistered ? (
          <div className="registration-complete" role="status">
            <span className="eyebrow">{t('auth.registrationComplete')}</span>
            <h1>{t('auth.checkEmailTitle')}</h1>
            <p>{t('auth.checkEmailDescription', { email })}</p>
            <Link className="primary-link" to="/login" state={{ from: destination }}>
              {t('auth.backToLogin')}
            </Link>
          </div>
        ) : (
          <>
            <div className="login-heading">
              <span className="eyebrow">{t('auth.joinCatalogue')}</span>
              <h1>{t('auth.registerTitle')}</h1>
              <p>{t('auth.registerDescription')}</p>
            </div>
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
              <label htmlFor="email">{t('auth.email')}</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <label htmlFor="password">{t('auth.password')}</label>
              <input
                id="password"
                name="password"
                type="password"
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              <p className="field-help">{t('auth.passwordHelp')}</p>
              <label htmlFor="confirm-password">{t('auth.confirmPasswordField')}</label>
              <input
                id="confirm-password"
                name="confirmPassword"
                type="password"
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="primary-button" type="submit" disabled={isSubmitting}>
                {isSubmitting ? t('auth.registering') : t('auth.register')}
              </button>
            </form>
            <p className="auth-switch">
              {t('auth.alreadyAccount')}{' '}
              <Link to="/login" state={{ from: destination }}>{t('auth.login')}</Link>
            </p>
          </>
        )}
      </div>
    </section>
  )
}
