import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { changePassword, createApiKey, listApiKeys, revokeApiKey } from '../api/auth.js'
import { useAuth } from '../auth/useAuth.js'
import { ProfilePage } from './ProfilePage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/auth.js', () => ({
  changePassword: vi.fn(),
  createApiKey: vi.fn(),
  listApiKeys: vi.fn(),
  revokeApiKey: vi.fn(),
}))
vi.mock('../i18n.js', () => ({
  CHINESE: 'zh-cn',
  ENGLISH: 'en-uk',
  changeLocale: vi.fn(),
  getCurrentLocale: vi.fn(() => 'en-uk'),
}))

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

function renderPage() {
  return render(<MemoryRouter initialEntries={['/profile']}><Routes>
    <Route path="/profile" element={<><ProfilePage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({
    user: { id: 'user-1', username: 'alice' }, isLoading: false, deleteAccount: vi.fn(),
  })
  changePassword.mockReset()
  createApiKey.mockReset()
  listApiKeys.mockReset().mockResolvedValue([])
  revokeApiKey.mockReset()
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false, deleteAccount: vi.fn() })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

it('validates password confirmation before submitting a password change', async () => {
  const user = userEvent.setup()
  renderPage()
  await user.type(screen.getByLabelText('Current password'), 'current-password')
  await user.type(screen.getByLabelText('New password'), 'StrongPassword1!')
  await user.type(screen.getByLabelText('Confirm new password'), 'DifferentPassword1!')
  await user.click(screen.getByRole('button', { name: 'Change password' }))
  expect(screen.getByRole('alert')).toHaveTextContent('do not match')
  expect(changePassword).not.toHaveBeenCalled()
})

it('creates and revokes API keys from the profile page', async () => {
  listApiKeys.mockResolvedValue([{ id: 'key-1', name: 'Old key', expiresAt: null }])
  createApiKey.mockResolvedValue({
    id: 'key-2',
    key: 'secret',
    name: 'CLI key',
    createdAt: '2026-08-20T20:00:00Z',
    expiresAt: null,
  })
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByText('Old key')).toBeInTheDocument()

  await user.type(screen.getByLabelText('Key name'), 'CLI key')
  await user.click(screen.getByRole('button', { name: 'Create API key' }))
  await waitFor(() => expect(createApiKey).toHaveBeenCalledWith('CLI key', 'oneMonth'))
  expect(await screen.findByRole('status')).toHaveTextContent('key-2:secret')

  await user.click(screen.getAllByRole('button', { name: 'Revoke' })[0])
  await waitFor(() => expect(revokeApiKey).toHaveBeenCalled())
})
