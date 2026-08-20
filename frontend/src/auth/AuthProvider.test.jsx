import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth.js'
import { AuthProvider } from './AuthProvider.jsx'
import { useAuth } from './useAuth.js'

vi.mock('../api/auth.js')

function Consumer() {
  const { user, isLoading, login, logout } = useAuth()
  return <div>
    <span>{isLoading ? 'loading' : user?.username ?? 'anonymous'}</span>
    <button onClick={() => login('alice', 'password')}>login</button>
    <button onClick={logout}>logout</button>
  </div>
}

beforeEach(() => {
  authApi.getCurrentUser.mockReset()
  authApi.login.mockReset()
  authApi.logout.mockReset()
})

it('loads the current session and updates state after logout', async () => {
  authApi.getCurrentUser.mockResolvedValue({ id: 'user', username: 'alice' })
  authApi.logout.mockResolvedValue()
  const user = userEvent.setup()
  render(<AuthProvider><Consumer /></AuthProvider>)
  expect(screen.getByText('loading')).toBeInTheDocument()
  await screen.findByText('alice')
  await user.click(screen.getByRole('button', { name: 'logout' }))
  expect(screen.getByText('anonymous')).toBeInTheDocument()
})

it('treats a failed session lookup as anonymous and supports login', async () => {
  authApi.getCurrentUser.mockRejectedValue(new Error('unauthorized'))
  authApi.login.mockResolvedValue({ id: 'user', username: 'alice' })
  const user = userEvent.setup()
  render(<AuthProvider><Consumer /></AuthProvider>)
  await screen.findByText('anonymous')
  await user.click(screen.getByRole('button', { name: 'login' }))
  await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument())
  expect(authApi.login).toHaveBeenCalledWith('alice', 'password')
})
