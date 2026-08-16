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
