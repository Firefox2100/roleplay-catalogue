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

async function getCsrfToken() {
  const response = await request('/api/auth/csrf')
  return (await response.json()).csrfToken
}

export async function getCurrentUser() {
  return (await request('/api/auth/me')).json()
}

export async function login(username, password) {
  const csrfToken = await getCsrfToken()
  await request('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify({ username, password }),
  })
  return getCurrentUser()
}

export async function logout() {
  const csrfToken = await getCsrfToken()
  await request('/api/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  })
}

export async function register(username, email, password) {
  const csrfToken = await getCsrfToken()
  await request('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify({ username, email, password }),
  })
}

async function authenticatedRequest(path, method, body) {
  const csrfToken = await getCsrfToken()
  return request(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify(body),
  })
}

export async function listApiKeys() {
  return (await request('/api/auth/api-keys')).json()
}

export async function createApiKey(name, lifetime) {
  const response = await authenticatedRequest('/api/auth/api-keys', 'POST', { name, lifetime })
  return response.json()
}

export async function revokeApiKey(keyId) {
  await authenticatedRequest(`/api/auth/api-keys/${encodeURIComponent(keyId)}`, 'DELETE')
}

export async function changePassword(currentPassword, newPassword) {
  await authenticatedRequest('/api/auth/password', 'POST', { currentPassword, newPassword })
}

export async function deleteAccount(password) {
  await authenticatedRequest('/api/auth/account', 'DELETE', { password })
}

export async function requestPasswordReset(email) {
  await authenticatedRequest('/api/auth/password-reset/request', 'POST', { email })
}

export async function confirmPasswordReset(userId, token, newPassword) {
  await authenticatedRequest('/api/auth/password-reset/confirm', 'POST', {
    userId, token, newPassword,
  })
}
