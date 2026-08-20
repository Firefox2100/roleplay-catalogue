import { useState } from 'react'
import { useTranslation } from 'react-i18next'

function displayValue(value) {
  if (value === undefined) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return JSON.stringify(value, null, 2)
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function humanizeFieldName(field) {
  return field
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/^./, (char) => char.toUpperCase())
}

// Shown when a save is rejected because someone else changed the same draft first. `conflicts`
// is the `threeWayMerge` output: fields changed on both sides in different ways. Every other
// field already merged automatically and needs no attention here. The user picks a side per
// conflicting field; "Apply & retry" folds that choice into `merged` and re-submits the save.
export function ConflictResolutionModal({ fieldLabel = humanizeFieldName, conflicts, merged, onApply, onCancel, isRetrying }) {
  const { t } = useTranslation()
  const fields = Object.keys(conflicts)
  const [resolutions, setResolutions] = useState(
    () => Object.fromEntries(fields.map((field) => [field, 'local'])),
  )

  function apply() {
    const resolved = { ...merged }
    for (const field of fields) {
      const conflict = conflicts[field]
      if (conflict.entries) continue // keyed-array conflicts: local default from `merged` stands.
      resolved[field] = resolutions[field] === 'remote' ? conflict.remote : conflict.local
    }
    onApply(resolved)
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !isRetrying) onCancel()
    }}>
      <div className="conflict-resolution-dialog" role="dialog" aria-modal="true"
        aria-labelledby="conflict-resolution-heading">
        <h2 id="conflict-resolution-heading">{t('editor.conflictTitle')}</h2>
        <p>{t('editor.conflictBody')}</p>
        <div className="conflict-fields">
          {fields.map((field) => {
            const conflict = conflicts[field]
            const label = fieldLabel?.(field) ?? field
            if (conflict.entries) {
              return (
                <div className="conflict-field" key={field}>
                  <h3>{label}</h3>
                  <p className="field-help">
                    {t('editor.conflictEntriesNote', { count: Object.keys(conflict.entries).length })}
                  </p>
                </div>
              )
            }
            return (
              <fieldset className="conflict-field" key={field}>
                <legend>{label}</legend>
                <label className="conflict-option">
                  <input type="radio" name={`conflict-${field}`} checked={resolutions[field] === 'local'}
                    onChange={() => setResolutions((current) => ({ ...current, [field]: 'local' }))} />
                  <span>{t('editor.conflictKeepMine')}</span>
                  <pre>{displayValue(conflict.local)}</pre>
                </label>
                <label className="conflict-option">
                  <input type="radio" name={`conflict-${field}`} checked={resolutions[field] === 'remote'}
                    onChange={() => setResolutions((current) => ({ ...current, [field]: 'remote' }))} />
                  <span>{t('editor.conflictTakeTheirs')}</span>
                  <pre>{displayValue(conflict.remote)}</pre>
                </label>
              </fieldset>
            )
          })}
        </div>
        <div className="modal-actions">
          <button type="button" disabled={isRetrying} onClick={onCancel}>{t('editor.conflictCancel')}</button>
          <button className="save-button" type="button" disabled={isRetrying} onClick={apply}>
            {isRetrying ? t('editor.conflictApplying') : t('editor.conflictApply')}
          </button>
        </div>
      </div>
    </div>
  )
}
