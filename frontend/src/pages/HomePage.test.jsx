import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { listResources, resourceImageUrl } from '../api/resources.js'
import { HomePage } from './HomePage.jsx'

vi.mock('../api/resources.js', () => ({
  listResources: vi.fn(),
  resourceImageUrl: vi.fn(() => null),
  suggestResourceTags: vi.fn(() => Promise.resolve([])),
}))

const resource = {
  id: 'character-1', resourceType: 'sillytavern/character', authorUsername: 'alice',
  metadata: { name: 'Aster', description: 'A helpful character', tags: ['fantasy'] },
  viewCount: 1234, downloadCount: 56,
}

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

beforeEach(() => {
  listResources.mockReset().mockResolvedValue({ items: [resource], nextOffset: null })
  resourceImageUrl.mockReturnValue(null)
})

it('loads catalogue cards with metrics and navigates to details', async () => {
  const user = userEvent.setup()
  render(<MemoryRouter><Routes>
    <Route path="*" element={<><HomePage /><Location /></>} />
  </Routes></MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Aster' })).toBeInTheDocument()
  expect(screen.getByTitle('Views')).toHaveTextContent('1,234')
  expect(screen.getByTitle('Downloads')).toHaveTextContent('56')
  await user.click(screen.getByRole('heading', { name: 'Aster' }))
  expect(screen.getByTestId('location')).toHaveTextContent('/characters/character-1')
})

it('applies search and author filters through the resource API', async () => {
  const user = userEvent.setup()
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  await screen.findByRole('heading', { name: 'Aster' })
  await user.type(screen.getByRole('searchbox'), 'hero')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => expect(listResources).toHaveBeenLastCalledWith(expect.objectContaining({
    searchString: 'hero',
  })))
  await user.click(screen.getByRole('button', { name: 'alice' }))
  await waitFor(() => expect(listResources).toHaveBeenLastCalledWith(expect.objectContaining({
    author: 'alice',
  })))
})

it('shows a recoverable error when catalogue loading fails', async () => {
  listResources.mockRejectedValue(new Error('offline'))
  render(<MemoryRouter><HomePage /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Resources could not be loaded')
})
