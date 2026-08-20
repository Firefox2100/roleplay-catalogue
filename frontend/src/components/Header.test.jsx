import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { useAuth } from '../auth/useAuth.js'
import { Header } from './Header.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

beforeEach(() => useAuth.mockReset())

it('preserves the current destination in anonymous login links', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  render(<MemoryRouter initialEntries={['/resources/new?kind=image']}><Header /></MemoryRouter>)
  expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
})

it('opens the account menu, closes on Escape, and logs out', async () => {
  const logout = vi.fn().mockResolvedValue()
  useAuth.mockReturnValue({ user: { username: 'alice' }, isLoading: false, logout })
  const user = userEvent.setup()
  render(<MemoryRouter initialEntries={['/profile']}><Routes>
    <Route path="*" element={<><Header /><Location /></>} />
  </Routes></MemoryRouter>)
  await user.click(screen.getByRole('button', { name: /alice/ }))
  expect(screen.getByRole('menu')).toBeInTheDocument()
  fireEvent.keyDown(document, { key: 'Escape' })
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /alice/ }))
  await user.click(screen.getByRole('menuitem', { name: 'Log out' }))
  expect(logout).toHaveBeenCalled()
  expect(screen.getByTestId('location')).toHaveTextContent('/')
})
