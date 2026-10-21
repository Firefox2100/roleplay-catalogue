import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'

function UserMenu({ username }) {
  const { t } = useTranslation()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const menuRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    if (!isOpen) return undefined
    const closeMenu = (event) => {
      if (!menuRef.current?.contains(event.target)) setIsOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('pointerdown', closeMenu)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeMenu)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [isOpen])

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
      setIsOpen(false)
      void navigate('/')
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        type="button"
        className="account-button"
        aria-expanded={isOpen}
        aria-haspopup="menu"
        onClick={() => setIsOpen((open) => !open)}
      >
        <span className="account-avatar" aria-hidden="true">
          {username.slice(0, 1).toUpperCase()}
        </span>
        <span>{username}</span>
        <span className="chevron" aria-hidden="true">⌄</span>
      </button>
      {isOpen && (
        <div className="account-dropdown" role="menu">
          <Link to="/profile" role="menuitem" onClick={() => setIsOpen(false)}>
            {t('account.profile')}
          </Link>
          <Link to="/resources/mine" role="menuitem" onClick={() => setIsOpen(false)}>
            {t('account.myResources')}
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            disabled={isLoggingOut}
          >
            {isLoggingOut ? t('auth.loggingOut') : t('auth.logout')}
          </button>
        </div>
      )}
    </div>
  )
}

export function Header() {
  const { t } = useTranslation()
  const { user, isLoading } = useAuth()
  const location = useLocation()
  const loginDestination = `${location.pathname}${location.search}${location.hash}`
  const [theme, setTheme] = useState(() => localStorage.getItem('roleplay-catalogue.theme') || 'light')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('roleplay-catalogue.theme', theme)
  }, [theme])

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" to="/" aria-label={t('app.homeLabel')}>
          <span className="brand-mark" aria-hidden="true">RC</span>
          <span className="brand-copy">
            <strong>{t('app.title')}</strong>
            <small>{t('app.tagline')}</small>
          </span>
        </Link>
        <nav className="main-nav" aria-label={t('nav.primary')}>
          <NavLink to="/" end>{t('nav.home')}</NavLink>
          <NavLink to="/resources/new">{t('nav.new')}</NavLink>
        </nav>
        <div className="header-account">
          <button className="theme-toggle" type="button"
            aria-label={t(theme === 'light' ? 'theme.switchDark' : 'theme.switchLight')}
            onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}>
            {theme === 'light' ? (
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/><circle cx="12" cy="12" r="4"/></svg>
            ) : (
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20 15.3A8.5 8.5 0 0 1 8.7 4a8.5 8.5 0 1 0 11.3 11.3Z"/></svg>
            )}
          </button>
          {isLoading ? (
            <span className="account-placeholder" aria-label={t('auth.checkingSession')} />
          ) : user ? (
            <UserMenu username={user.username} />
          ) : (
            <Link className="login-link" to="/login" state={{ from: loginDestination }}>
              {t('auth.login')}
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
