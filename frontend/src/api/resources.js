class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, options = {}) {
  const response = await fetch(path, { credentials: 'include', ...options })
  if (!response.ok) {
    let message = response.statusText
    try {
      const body = await response.json()
      message = body.detail ?? message
    } catch {
      // The response may intentionally have no JSON body.
    }
    throw new ApiError(message, response.status)
  }
  return response
}

export async function createResource(resource) {
  const csrfResponse = await request('/api/auth/csrf')
  const csrfToken = (await csrfResponse.json()).csrfToken
  const response = await request('/api/resources', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify(resource),
  })
  return response.json()
}

export async function listResources({ resourceType, tags = [], author = '', limit, offset,
  publishedOnly = false, searchString = '' } = {}) {
  const query = new URLSearchParams()
  if (resourceType) query.set('resourceType', resourceType)
  tags.forEach((tag) => query.append('tags', tag))
  if (author) query.set('author', author)
  if (limit) query.set('limit', limit)
  if (offset) query.set('offset', offset)
  if (publishedOnly) query.set('publishedOnly', 'true')
  if (searchString.trim()) query.set('search_string', searchString.trim())
  const suffix = query.size ? `?${query}` : ''
  return (await request(`/api/resources${suffix}`)).json()
}

export async function deleteResource(resourceId, resourceType) {
  const path = resourceType === 'core/image' ? `/api/images/${resourceId}` : `/api/resources/${resourceId}`
  await request(path, { method: 'DELETE', headers: await csrfHeaders() })
}

export async function suggestResourceTags(search, limit = 10) {
  const query = new URLSearchParams({ search, limit })
  return (await request(`/api/resources/tags?${query}`)).json()
}

export async function updateResource(resourceId, metadata) {
  const csrfResponse = await request('/api/auth/csrf')
  const csrfToken = (await csrfResponse.json()).csrfToken
  const response = await request(`/api/resources/${resourceId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify(metadata),
  })
  return response.json()
}

async function csrfHeaders() {
  const csrfResponse = await request('/api/auth/csrf')
  return { 'X-CSRF-Token': (await csrfResponse.json()).csrfToken }
}

export async function uploadImageResource({ name, description, visibility, tags, file }) {
  const form = new FormData()
  form.append('name', name)
  form.append('description', description)
  form.append('visibility', visibility)
  tags.forEach((tag) => form.append('tags', tag))
  form.append('file', file)
  return (await request('/api/images', {
    method: 'POST', headers: await csrfHeaders(), body: form,
  })).json()
}

export async function uploadCharacterCover(resourceId, file) {
  const form = new FormData()
  form.append('file', file)
  return (await request(`/api/images/covers/${resourceId}`, {
    method: 'POST', headers: await csrfHeaders(), body: form,
  })).json()
}

export async function selectCharacterCover(resourceId, imageResourceId) {
  return (await request(`/api/images/covers/${resourceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...await csrfHeaders() },
    body: JSON.stringify({ imageResourceId }),
  })).json()
}

export function imageContentUrl(imageResourceId) {
  return `/api/images/${imageResourceId}/content`
}

export function resourceImageUrl(resource) {
  if (resource.resourceType === 'core/image') return imageContentUrl(resource.id)
  if (resource.coverImageResourceId) return `/api/images/covers/resources/${resource.id}`
  return null
}

export async function updateImageMetadata(resourceId, metadata) {
  return (await request(`/api/images/${resourceId}/metadata`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...await csrfHeaders() },
    body: JSON.stringify(metadata),
  })).json()
}

export async function importCharacterCard(resourceId, file) {
  const form = new FormData()
  form.append('file', file)
  return (await request(`/api/resources/${resourceId}/import-card`, {
    method: 'POST', headers: await csrfHeaders(), body: form,
  })).json()
}

export async function importLorebook(resourceId, file) {
  const form = new FormData()
  form.append('file', file)
  return (await request(`/api/resources/${resourceId}/import-lorebook`, {
    method: 'POST', headers: await csrfHeaders(), body: form,
  })).json()
}

export async function getResource(resourceId) {
  return (await request(`/api/resources/${resourceId}`)).json()
}

export async function getResourceData(resourceId) {
  return (await request(`/api/resources/${resourceId}/data`)).json()
}

export async function saveResourceData(resourceId, data) {
  const csrfResponse = await request('/api/auth/csrf')
  const csrfToken = (await csrfResponse.json()).csrfToken
  const response = await request(`/api/resources/${resourceId}/data`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify({ data }),
  })
  return response.json()
}

export async function publishResource(resourceId, version) {
  return (await request(`/api/versions/${resourceId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...await csrfHeaders() },
    body: JSON.stringify({ version }),
  })).json()
}

export async function listResourceVersions(resourceId) {
  return (await request(`/api/versions/resource/${resourceId}`)).json()
}

export async function updateVersionVisibility(versionId, visibility) {
  return (await request(`/api/versions/${versionId}/visibility`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...await csrfHeaders() },
    body: JSON.stringify({ visibility }),
  })).json()
}

export async function getResourceVersionData(versionId) {
  return (await request(`/api/versions/${versionId}/data`)).json()
}

export function draftDownloadUrl(resourceId) {
  return `/api/versions/draft/${resourceId}/download`
}

export function versionDownloadUrl(versionId) {
  return `/api/versions/${versionId}/download`
}

export function versionCoverUrl(versionId) {
  return `/api/images/covers/versions/${versionId}`
}

export async function createSignedDownloadUrl(versionId) {
  return (await request(`/api/versions/${versionId}/signed-download`)).json()
}

export async function forkResourceVersion(versionId) {
  return (await request(`/api/versions/${versionId}/fork`, {
    method: 'POST',
    headers: await csrfHeaders(),
  })).json()
}
