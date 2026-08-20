import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createSignedDownloadUrl, listResources, saveResourceData, updateResource,
} from './resources.js'

function response(body, { ok = true, status = 200, statusText = 'OK' } = {}) {
  return { ok, status, statusText, json: vi.fn().mockResolvedValue(body) }
}

describe('resources API', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()))

  it('builds list filters and always sends credentials', async () => {
    fetch.mockResolvedValue(response({ items: [], nextOffset: null }))
    await listResources({
      resourceType: 'core/image', tags: ['art', 'portrait'], author: 'alice',
      offset: 20, limit: 10, publishedOnly: true, searchString: ' hero ',
    })
    const [url, options] = fetch.mock.calls[0]
    const parsed = new URL(url, 'https://catalogue.test')
    expect(parsed.pathname).toBe('/api/resources')
    expect(parsed.searchParams.getAll('tags')).toEqual(['art', 'portrait'])
    expect(parsed.searchParams.get('search_string')).toBe('hero')
    expect(parsed.searchParams.get('publishedOnly')).toBe('true')
    expect(options.credentials).toBe('include')
  })

  it('sends the optimistic-lock ETag and CSRF token on metadata writes', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'resource', revision: 8 }))
    await updateResource('resource', { name: 'Updated' }, 7)
    expect(fetch.mock.calls[1]).toEqual([
      '/api/resources/resource',
      expect.objectContaining({
        method: 'PUT', credentials: 'include',
        headers: expect.objectContaining({ 'If-Match': '"7"', 'X-CSRF-Token': 'csrf' }),
      }),
    ])
  })

  it('omits If-Match when creating draft data for the first time', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ revision: 0 }))
    await saveResourceData('resource', { name: 'Draft' })
    expect(fetch.mock.calls[1][1].headers).not.toHaveProperty('If-Match')
  })

  it('preserves structured 412 conflict details on API errors', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response(
        { detail: { message: 'Stale', current: { revision: 3 } } },
        { ok: false, status: 412, statusText: 'Precondition Failed' },
      ))
    await expect(updateResource('resource', { name: 'Mine' }, 2)).rejects.toMatchObject({
      name: 'ApiError', status: 412,
      body: { detail: { message: 'Stale', current: { revision: 3 } } },
      message: 'Stale',
    })
  })

  it('returns signed download metadata unchanged', async () => {
    fetch.mockResolvedValue(response({ url: 'https://storage.test/file', expiresIn: 120 }))
    await expect(createSignedDownloadUrl('version')).resolves.toEqual({
      url: 'https://storage.test/file', expiresIn: 120,
    })
  })
})
