import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { confirmPasswordReset, requestPasswordReset } from '../api/auth.js'
import { useAuth } from '../auth/useAuth.js'
import { LoginPage } from './LoginPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/auth.js', () => ({
  confirmPasswordReset: vi.fn(), requestPasswordReset: vi.fn(),
}))

function Location() {
  const location = useLocation()
  return <span data-testid="location">{location.pathname}{location.search}</span>
}

function renderLogin(initial = '/login', state) {
  return render(<MemoryRouter initialEntries={[{ pathname: initial.split('?')[0],
    search: initial.includes('?') ? `?${initial.split('?')[1]}` : '', state }]}>
    <Routes><Route path="*" element={<><LoginPage /><Location /></>} /></Routes>
  </MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn() })
  confirmPasswordReset.mockReset()
  requestPasswordReset.mockReset()
})

describe('LoginPage', () => {
  it('logs in and returns to the protected destination', async () => {
    const login = vi.fn().mockResolvedValue({ username: 'alice' })
    useAuth.mockReturnValue({ user: null, isLoading: false, login })
    const user = userEvent.setup()
    renderLogin('/login', { from: '/profile' })
    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Password'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    expect(login).toHaveBeenCalledWith('alice', 'secret')
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/profile'))
  })

  it('shows the specific invalid-credentials error for a 401', async () => {
    const login = vi.fn().mockRejectedValue({ status: 401 })
    useAuth.mockReturnValue({ user: null, isLoading: false, login })
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText('Username'), 'alice')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('incorrect')
  })

  it('requests a reset without revealing whether the email exists', async () => {
    requestPasswordReset.mockResolvedValue()
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole('button', { name: 'Forgot password?' }))
    await user.type(screen.getByLabelText('Email address'), 'alice@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset link' }))
    expect(requestPasswordReset).toHaveBeenCalledWith('alice@example.com')
    expect(await screen.findByRole('status')).toBeInTheDocument()
  })

  it('validates and confirms a password-reset link', async () => {
    confirmPasswordReset.mockResolvedValue()
    const user = userEvent.setup()
    renderLogin('/reset-password?userId=user-1&token=reset-token')
    await user.type(screen.getByLabelText('New password'), 'NewPassword1!')
    await user.type(screen.getByLabelText('Confirm new password'), 'different')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))
    expect(screen.getByRole('alert')).toHaveTextContent('match')
    expect(confirmPasswordReset).not.toHaveBeenCalled()

    await user.clear(screen.getByLabelText('Confirm new password'))
    await user.type(screen.getByLabelText('Confirm new password'), 'NewPassword1!')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))
    await waitFor(() => expect(confirmPasswordReset).toHaveBeenCalledWith(
      'user-1', 'reset-token', 'NewPassword1!',
    ))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/login?reset=success'))
  })
})
