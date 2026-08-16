import { useTranslation } from 'react-i18next'

export function HomePage() {
  const { t } = useTranslation()
  return (
    <section className="home-page" aria-label={t('home.label')}>
      <h1 className="visually-hidden">{t('home.label')}</h1>
    </section>
  )
}
