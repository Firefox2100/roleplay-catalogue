import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { createResource, uploadImageResource } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { CreateResourcePage } from './CreateResourcePage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  createResource: vi.fn(), uploadImageResource: vi.fn(),
}))
vi.mock('../components/TagEditor.jsx', () => ({
  TagEditor: ({ onChange }) => <button type="button" onClick={() => onChange(['fantasy'])}>add tag</button>,
}))

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

function renderPage() {
  return render(<MemoryRouter initialEntries={['/resources/new']}><Routes>
    <Route path="/resources/new" element={<><CreateResourcePage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'user' }, isLoading: false })
  createResource.mockReset()
  uploadImageResource.mockReset()
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

it('creates a character and opens its editor', async () => {
  createResource.mockResolvedValue({
    id: 'character-1', resourceType: 'sillytavern/character', metadata: { name: 'Aster' },
  })
  const user = userEvent.setup()
  renderPage()
  await user.type(screen.getByLabelText('Name'), 'Aster')
  await user.selectOptions(screen.getByLabelText('Visibility'), 'public')
  await user.click(screen.getByRole('button', { name: 'add tag' }))
  await user.click(screen.getByRole('button', { name: 'Create resource' }))
  expect(createResource).toHaveBeenCalledWith(expect.objectContaining({
    name: 'Aster', resourceType: 'sillytavern/character', visibility: 'public', tags: ['fantasy'],
  }))
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(
    '/resources/character-1/edit',
  ))
})

it('uploads image resources and shows their completion summary', async () => {
  uploadImageResource.mockResolvedValue({
    id: 'image-1', resourceType: 'core/image', metadata: { name: 'Portrait' },
  })
  const user = userEvent.setup()
  renderPage()
  await user.type(screen.getByLabelText('Name'), 'Portrait')
  await user.selectOptions(screen.getByLabelText('Resource type'), 'core/image')
  const file = new File(['image'], 'portrait.png', { type: 'image/png' })
  const input = screen.getByLabelText(/Image file/)
  await user.upload(input, file)
  expect(input.files[0]).toBe(file)
  fireEvent.submit(screen.getByRole('button', { name: 'Create resource' }).closest('form'))
  await waitFor(() => expect(uploadImageResource).toHaveBeenCalledWith(expect.objectContaining({
    name: 'Portrait', file,
  })))
  expect(await screen.findByRole('status')).toHaveTextContent('Portrait')
  await user.click(screen.getByRole('button', { name: 'Create another' }))
  expect(screen.getByRole('button', { name: 'Create resource' })).toBeInTheDocument()
})

it('reports expired sessions distinctly', async () => {
  createResource.mockRejectedValue({ status: 401 })
  const user = userEvent.setup()
  renderPage()
  await user.type(screen.getByLabelText('Name'), 'Aster')
  await user.click(screen.getByRole('button', { name: 'Create resource' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('session has expired')
})
