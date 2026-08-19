import { useTranslation } from 'react-i18next'

export function ResourceAuthors({ resource }) {
  const { t } = useTranslation()
  return (
    <>
      <section className="detail-field"><h3>{t('details.author')}</h3><p>{resource.authorUsername}</p></section>
      {resource.coAuthorUsernames?.length > 0 && (
        <section className="detail-field"><h3>{t('details.coAuthors')}</h3>
          <p>{resource.coAuthorUsernames.join(', ')}</p></section>
      )}
    </>
  )
}
