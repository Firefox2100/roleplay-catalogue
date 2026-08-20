import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import '../i18n.js'

afterEach(() => {
  document.body.innerHTML = ''
})
