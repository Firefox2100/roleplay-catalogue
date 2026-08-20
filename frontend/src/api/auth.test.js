import { beforeEach, describe, expect, it, vi } from 'vitest'
import { login, logout, register } from './auth.js'

const ok = (body = {}) => ({
  ok: true, status: 200, statusText: 'OK', json: vi.fn().mockResolvedValue(body),
})

describe('auth API', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()))

  it('logs in using CSRF and then fetches the current user', async () => {
    fetch
      .mockResolvedValueOnce(ok({ csrfToken: 'csrf-token' }))
      .mockResolvedValueOnce(ok())
      .mockResolvedValueOnce(ok({ id: 'user', username: 'alice' }))
    await expect(login('alice', 'secret')).resolves.toMatchObject({ username: 'alice' })
    expect(fetch.mock.calls[1][1]).toMatchObject({
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': 'csrf-token' },
      body: JSON.stringify({ username: 'alice', password: 'secret' }),
    })
    expect(fetch.mock.calls[2][0]).toBe('/api/auth/me')
  })

  it.each([
    ['register', () => register('alice', 'a@example.com', 'Password1!'), '/api/auth/register'],
    ['logout', () => logout(), '/api/auth/logout'],
  ])('protects %s with a CSRF token', async (_name, operation, expectedPath) => {
    fetch.mockResolvedValueOnce(ok({ csrfToken: 'csrf' })).mockResolvedValueOnce(ok())
    await operation()
    expect(fetch.mock.calls[1][0]).toBe(expectedPath)
    expect(fetch.mock.calls[1][1].headers['X-CSRF-Token']).toBe('csrf')
  })

  it('surfaces a backend error message', async () => {
    fetch.mockResolvedValue({
      ok: false, status: 401, statusText: 'Unauthorized',
      json: vi.fn().mockResolvedValue({ detail: 'Wrong password' }),
    })
    await expect(login('alice', 'wrong')).rejects.toMatchObject({
      status: 401, message: 'Wrong password',
    })
  })
})
