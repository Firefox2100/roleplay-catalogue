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

export async function listResources({ resourceType, tags = [], author = '', limit,
  publishedOnly = false } = {}) {
  const query = new URLSearchParams()
  if (resourceType) query.set('resourceType', resourceType)
  tags.forEach((tag) => query.append('tags', tag))
  if (author) query.set('author', author)
  if (limit) query.set('limit', limit)
  if (publishedOnly) query.set('publishedOnly', 'true')
  const suffix = query.size ? `?${query}` : ''
  return (await request(`/api/resources${suffix}`)).json()
}

export async function suggestResourceTags(search) {
  const query = new URLSearchParams({ search })
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
