import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { suggestResourceTags } from '../api/resources.js'

export function TagEditor({ id, value, onChange, allowCreate = true, showPopular = false }) {
  const { t } = useTranslation()
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [popularTags, setPopularTags] = useState([])
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    if (!input.trim()) {
      return undefined
    }
    let active = true
    const timeout = setTimeout(() => {
      suggestResourceTags(input.trim(), 10)
        .then((items) => { if (active) setSuggestions(items) })
        .catch(() => { if (active) setSuggestions([]) })
    }, 150)
    return () => {
      active = false
      clearTimeout(timeout)
    }
  }, [input])

  useEffect(() => {
    if (!showPopular) return undefined
    let active = true
    suggestResourceTags('', 5)
      .then((items) => { if (active) setPopularTags(items) })
      .catch(() => { if (active) setPopularTags([]) })
    return () => { active = false }
  }, [showPopular])

  function addTag(tag) {
    const normalised = tag.trim()
    if (!normalised) return
    const duplicate = value.some((item) => (
      item.toLocaleLowerCase() === normalised.toLocaleLowerCase()
    ))
    if (!duplicate) onChange([...value, normalised])
    setInput('')
    setSuggestions([])
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      const exactSuggestion = suggestions.find((tag) => (
        tag.toLocaleLowerCase() === input.trim().toLocaleLowerCase()
      ))
      if (allowCreate || exactSuggestion) addTag(exactSuggestion ?? input)
    } else if (event.key === 'Backspace' && !input && value.length) {
      onChange(value.slice(0, -1))
    }
  }

  return (
    <div className="tag-editor">
      <div className="tag-editor-input">
        {value.map((tag) => (
          <span className="tag-chip" key={tag}>{tag}
            <button type="button" aria-label={t('tags.remove', { tag })}
              onClick={() => onChange(value.filter((item) => item !== tag))}>×</button>
          </span>
        ))}
        <input id={id} value={input} placeholder={value.length ? '' : t('tags.placeholder')}
          onChange={(event) => { setInput(event.target.value); setSuggestions([]) }}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)} onBlur={() => setTimeout(() => setIsFocused(false), 120)} />
        {isFocused && input.trim() && (
          <div className="tag-suggestions" role="listbox">
            {suggestions.filter((tag) => !value.some((selected) => (
              selected.toLocaleLowerCase() === tag.toLocaleLowerCase()
            ))).map((tag) => (
              <button key={tag} type="button" role="option" onMouseDown={(event) => event.preventDefault()}
                onClick={() => addTag(tag)}>{tag}</button>
            ))}
            {allowCreate && input.trim() &&
              !suggestions.some((tag) => tag.toLocaleLowerCase() === input.trim().toLocaleLowerCase()) && (
              <button type="button" className="create-tag-option"
                onMouseDown={(event) => event.preventDefault()} onClick={() => addTag(input)}>
                {t('tags.create', { tag: input.trim() })}
              </button>
            )}
          </div>
        )}
      </div>
      {showPopular && popularTags.length > 0 && (
        <div className="popular-tags" aria-label={t('tags.popular')}>
          <span>{t('tags.popular')}</span>
          {popularTags.filter((tag) => !value.some((selected) => (
            selected.toLocaleLowerCase() === tag.toLocaleLowerCase()
          ))).map((tag) => (
            <button key={tag} type="button" onClick={() => addTag(tag)}>{tag}</button>
          ))}
        </div>
      )}
      <p className="field-help">{t('tags.help')}</p>
    </div>
  )
}
