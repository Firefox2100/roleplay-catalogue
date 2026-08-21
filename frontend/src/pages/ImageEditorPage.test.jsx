import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { deleteResource, getResource, imageContentUrl, updateImageMetadata } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { ImageEditorPage } from './ImageEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  deleteResource: vi.fn(),
  getResource: vi.fn(),
  imageContentUrl: vi.fn(() => '/images/content'),
  updateImageMetadata: vi.fn(),
}))
vi.mock('../components/ResourceImage.jsx', () => ({ ResourceImage: () => <div>image</div> }))
vi.mock('../components/TagEditor.jsx', () => ({ TagEditor: () => <div>tag-editor</div> }))
vi.mock('../components/CoAuthorEditor.jsx', () => ({ CoAuthorEditor: () => <div>coauthors</div> }))
vi.mock('../components/ConflictResolutionModal.jsx', () => ({ ConflictResolutionModal: () => <div>conflict</div> }))
vi.mock('../hooks/useConflictAwareSave.js', () => ({
  useConflictAwareSave: vi.fn((config) => ({
    attempt: vi.fn((payload, _base, revision) => config.apiSave(payload, revision)),
    retry: vi.fn(),
    conflict: null,
    isRetrying: false,
    cancel: vi.fn(),
  })),
}))

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

function renderPage() {
  return render(<MemoryRouter initialEntries={['/images/image-1/edit']}><Routes>
    <Route path="/images/:resourceId/edit" element={<><ImageEditorPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1', username: 'alice' }, isLoading: false })
  getResource.mockReset().mockResolvedValue({
    id: 'image-1',
    authorId: 'author-1',
    resourceType: 'core/image',
    revision: 'rev-1',
    metadata: {
      name: 'Portrait',
      description: 'Artwork',
      language: 'en-uk',
      visibility: 'private',
      tags: ['portrait'],
    },
  })
  updateImageMetadata.mockReset().mockResolvedValue({
    id: 'image-1',
    authorId: 'author-1',
    resourceType: 'core/image',
    revision: 'rev-2',
    metadata: {
      name: 'Updated portrait',
      description: 'Artwork',
      language: 'en-uk',
      visibility: 'private',
      tags: ['portrait'],
    },
  })
  deleteResource.mockReset().mockResolvedValue()
  imageContentUrl.mockClear()
})

it('loads image metadata and saves updates', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Portrait' })).toBeInTheDocument()
  await user.clear(screen.getByLabelText('Name'))
  await user.type(screen.getByLabelText('Name'), 'Updated portrait')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateImageMetadata).toHaveBeenCalledWith(
    'image-1',
    expect.objectContaining({ name: 'Updated portrait' }),
    'rev-1',
  ))
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

