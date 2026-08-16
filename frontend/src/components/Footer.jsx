import { useTranslation } from 'react-i18next'

export function Footer() {
  const { t } = useTranslation()
  return (
    <footer className="site-footer">
      <span>{t('footer.project')}</span>
      <span>{t('footer.copyright', { year: new Date().getFullYear() })}</span>
    </footer>
  )
}
