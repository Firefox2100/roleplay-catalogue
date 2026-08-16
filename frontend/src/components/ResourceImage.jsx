import { useEffect, useRef, useState } from 'react'
import { imageContentUrl } from '../api/resources.js'

export function ResourceImage({ imageResourceId, src, alt = '', className = '' }) {
  const [attempt, setAttempt] = useState(0)
  const retryTimer = useRef(null)

  useEffect(() => () => clearTimeout(retryTimer.current), [])

  function retry() {
    if (attempt >= 5) return
    retryTimer.current = setTimeout(() => {
      setAttempt((current) => current + 1)
    }, 350 * (attempt + 1))
  }

  const imageUrl = src || imageContentUrl(imageResourceId)
  const separator = imageUrl.includes('?') ? '&' : '?'
  return (
    <img className={className}
      src={`${imageUrl}${separator}attempt=${attempt}`}
      alt={alt} onError={retry} />
  )
}
