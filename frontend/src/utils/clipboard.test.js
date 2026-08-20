import { afterEach, describe, expect, it, vi } from 'vitest'
import { copyText } from './clipboard.js'

describe('copyText', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uses the modern clipboard API when available', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    await copyText('download link')
    expect(writeText).toHaveBeenCalledWith('download link')
  })

  it('falls back to execCommand and removes its temporary element', async () => {
    vi.stubGlobal('navigator', {})
    document.execCommand = vi.fn(() => true)
    await copyText('fallback')
    expect(document.execCommand).toHaveBeenCalledWith('copy')
    expect(document.querySelector('textarea')).not.toBeInTheDocument()
  })

  it('rejects when the fallback cannot copy', async () => {
    vi.stubGlobal('navigator', {})
    document.execCommand = vi.fn(() => false)
    await expect(copyText('nope')).rejects.toThrow('Clipboard is unavailable')
  })
})
