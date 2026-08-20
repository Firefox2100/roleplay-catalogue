import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { register } from '../api/auth.js'
import { useAuth } from '../auth/useAuth.js'
import { RegisterPage } from './RegisterPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/auth.js', () => ({ register: vi.fn() }))

beforeEach(() => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  register.mockReset()
})

async function fillForm(user, password = 'GoodPassword1!', confirmation = password) {
  await user.type(screen.getByLabelText('Username'), 'alice')
  await user.type(screen.getByLabelText('Email address'), 'alice@example.com')
  await user.type(screen.getByLabelText('Password'), password)
  await user.type(screen.getByLabelText('Confirm password'), confirmation)
}

it('validates matching strong passwords before registration', async () => {
  const user = userEvent.setup()
  render(<MemoryRouter><RegisterPage /></MemoryRouter>)
  await fillForm(user, 'weak', 'different')
  await user.click(screen.getByRole('button', { name: 'Create account' }))
  expect(screen.getByRole('alert')).toHaveTextContent('match')
  expect(register).not.toHaveBeenCalled()
})

it('shows account conflicts returned by the API', async () => {
  register.mockRejectedValue({ status: 409 })
  const user = userEvent.setup()
  render(<MemoryRouter><RegisterPage /></MemoryRouter>)
  await fillForm(user)
  await user.click(screen.getByRole('button', { name: 'Create account' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('already')
})

it('submits registration and displays the activation-email confirmation', async () => {
  register.mockResolvedValue()
  const user = userEvent.setup()
  render(<MemoryRouter><RegisterPage /></MemoryRouter>)
  await fillForm(user)
  await user.click(screen.getByRole('button', { name: 'Create account' }))
  expect(register).toHaveBeenCalledWith('alice', 'alice@example.com', 'GoodPassword1!')
  expect(await screen.findByRole('status')).toHaveTextContent('alice@example.com')
})
