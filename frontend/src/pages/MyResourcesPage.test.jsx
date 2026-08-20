import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { listResources } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { MyResourcesPage } from './MyResourcesPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  listResources: vi.fn(), resourceImageUrl: vi.fn(() => null),
}))

const character = {
  id: 'character', resourceType: 'sillytavern/character', metadata: { name: 'Aster', description: '' },
  viewCount: 12, downloadCount: 3,
}
const image = {
  id: 'image', resourceType: 'core/image', metadata: { name: 'Portrait', description: '' },
  viewCount: 5, downloadCount: 1,
}

function Location() { return <span data-testid="location">{useLocation().pathname}</span> }
function renderPage() {
  return render(<MemoryRouter initialEntries={['/resources/mine']}><Routes>
    <Route path="/resources/mine" element={<><MyResourcesPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { username: 'alice' }, isLoading: false })
  listResources.mockReset().mockResolvedValue({ items: [character, image], nextOffset: null })
})

it('loads the current user resources, filters by type, and opens the correct editor', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Aster' })).toBeInTheDocument()
  expect(listResources).toHaveBeenCalledWith({ author: 'alice', limit: 50 })
  expect(screen.getAllByTitle('Views')[0]).toHaveTextContent('12')
  await user.click(screen.getByRole('tab', { name: 'Images' }))
  expect(screen.queryByRole('heading', { name: 'Aster' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('link', { name: 'Edit Portrait' }))
  expect(screen.getByTestId('location')).toHaveTextContent('/images/image/edit')
})

it('redirects anonymous users and reports loading errors', async () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})
