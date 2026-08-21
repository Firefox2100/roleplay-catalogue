import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  addCoAuthor, clearCharacterCover, createResource, createSignedDownloadUrl, deleteResource,
  draftDownloadUrl, forkResourceVersion, getResource, getResourceData, getResourceVersionData,
  imageContentUrl, importCharacterCard, importLorebook, importPreset, importWorldBundle,
  listResources, listResourceVersions, publishResource, removeCoAuthor, resourceImageUrl,
  saveResourceData, selectCharacterCover, suggestResourceTags, updateImageMetadata,
  updateResource, updateVersionVisibility, uploadCharacterCover, uploadImageResource,
  versionCoverUrl, versionDownloadUrl,
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

  it('creates resources with JSON and CSRF protection', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'created' }))
    await expect(createResource({ name: 'New' })).resolves.toEqual({ id: 'created' })
    expect(fetch.mock.calls[1]).toEqual(['/api/resources', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({
        'Content-Type': 'application/json', 'X-CSRF-Token': 'csrf',
      }),
      body: JSON.stringify({ name: 'New' }),
    })])
  })

  it('uses image deletion only for image resources', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'one' }))
      .mockResolvedValueOnce(response(null))
      .mockResolvedValueOnce(response({ csrfToken: 'two' }))
      .mockResolvedValueOnce(response(null))
    await deleteResource('image', 'core/image')
    await deleteResource('character', 'sillytavern/character')
    expect(fetch.mock.calls[1][0]).toBe('/api/images/image')
    expect(fetch.mock.calls[3][0]).toBe('/api/resources/character')
  })

  it('supports tags and co-author mutations', async () => {
    fetch
      .mockResolvedValueOnce(response(['fantasy']))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'resource' }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'resource' }))
    await expect(suggestResourceTags('fan', 4)).resolves.toEqual(['fantasy'])
    await addCoAuthor('resource', 'alice')
    await removeCoAuthor('resource', 'user-id')
    expect(fetch.mock.calls[2][1]).toEqual(expect.objectContaining({
      method: 'POST', body: JSON.stringify({ username: 'alice' }),
    }))
    expect(fetch.mock.calls[4][0]).toBe('/api/resources/resource/co-authors/user-id')
  })

  it('uploads image resources as multipart data', async () => {
    const file = new File(['png'], 'cover.png', { type: 'image/png' })
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'image' }))
    await uploadImageResource({
      name: 'Cover', description: 'Portrait', language: 'en-uk',
      visibility: 'private', tags: ['portrait', 'hero'], file,
    })
    const options = fetch.mock.calls[1][1]
    expect(options.method).toBe('POST')
    expect(options.body.getAll('tags')).toEqual(['portrait', 'hero'])
    expect(options.body.get('file')).toBe(file)
  })

  it('manages character covers and image metadata', async () => {
    const file = new File(['png'], 'cover.png')
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'cover' }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'resource' }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'resource', coverImageResourceId: null }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'cover', revision: 3 }))
    await uploadCharacterCover('resource', file)
    await selectCharacterCover('resource', 'cover')
    await clearCharacterCover('resource')
    await updateImageMetadata('cover', { name: 'Updated' }, 2)
    expect(fetch.mock.calls[3][1].body).toBe(JSON.stringify({ imageResourceId: 'cover' }))
    expect(fetch.mock.calls[7][1].headers['If-Match']).toBe('"2"')
  })

  it.each([
    [importCharacterCard, '/api/resources/resource/import-card'],
    [importLorebook, '/api/resources/resource/import-lorebook'],
    [importWorldBundle, '/api/resources/resource/import-world'],
    [importPreset, '/api/resources/resource/import-preset'],
  ])('uploads imports through the expected endpoint', async (operation, path) => {
    const file = new File(['data'], 'import.json')
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ draft: {} }))
    await operation('resource', file)
    expect(fetch.mock.calls[1][0]).toBe(path)
    expect(fetch.mock.calls[1][1].body.get('file')).toBe(file)
  })

  it('reads resources, draft data, versions and version data', async () => {
    fetch
      .mockResolvedValueOnce(response({ id: 'resource' }))
      .mockResolvedValueOnce(response({ data: {} }))
      .mockResolvedValueOnce(response([{ id: 'version' }]))
      .mockResolvedValueOnce(response({ data: { name: 'snapshot' } }))
    expect(await getResource('resource')).toEqual({ id: 'resource' })
    expect(await getResourceData('resource')).toEqual({ data: {} })
    expect(await listResourceVersions('resource')).toEqual([{ id: 'version' }])
    expect(await getResourceVersionData('version')).toEqual({ data: { name: 'snapshot' } })
  })

  it('publishes, changes visibility, and forks with CSRF protection', async () => {
    fetch
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'version' }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ visibility: 'public' }))
      .mockResolvedValueOnce(response({ csrfToken: 'csrf' }))
      .mockResolvedValueOnce(response({ id: 'fork' }))
    await publishResource('resource', 'v1')
    await updateVersionVisibility('version', 'public')
    await forkResourceVersion('version')
    expect(fetch.mock.calls[1][1].body).toBe(JSON.stringify({ version: 'v1' }))
    expect(fetch.mock.calls[3][1]).toEqual(expect.objectContaining({
      method: 'PATCH', body: JSON.stringify({ visibility: 'public' }),
    }))
    expect(fetch.mock.calls[5][1].method).toBe('POST')
  })

  it('builds content and download URLs for each resource shape', () => {
    expect(imageContentUrl('image')).toBe('/api/images/image/content')
    expect(resourceImageUrl({ id: 'image', resourceType: 'core/image' })).toBe('/api/images/image/content')
    expect(resourceImageUrl({ id: 'character', coverImageResourceId: 'cover' })).toBe('/api/images/covers/resources/character')
    expect(resourceImageUrl({ id: 'character' })).toBeNull()
    expect(draftDownloadUrl('resource')).toBe('/api/versions/draft/resource/download')
    expect(versionDownloadUrl('version')).toBe('/api/versions/version/download')
    expect(versionCoverUrl('version')).toBe('/api/images/covers/versions/version')
  })

  it('falls back to status text when an error body is not JSON', async () => {
    fetch.mockResolvedValue({
      ok: false, status: 503, statusText: 'Unavailable',
      json: vi.fn().mockRejectedValue(new SyntaxError('empty')),
    })
    await expect(getResource('resource')).rejects.toMatchObject({
      status: 503, message: 'Unavailable', body: undefined,
    })
  })
})
