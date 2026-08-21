import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  getResource,
  getResourceData,
  listResources,
  listResourceVersions,
  saveResourceData,
  updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { LorebookEditorPage } from './LorebookEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  clearCharacterCover: vi.fn(),
  deleteResource: vi.fn(),
  draftDownloadUrl: vi.fn(() => '/draft/download'),
  getResource: vi.fn(),
  getResourceData: vi.fn(),
  importLorebook: vi.fn(),
  listResources: vi.fn(),
  listResourceVersions: vi.fn(),
  publishResource: vi.fn(),
  saveResourceData: vi.fn(),
  selectCharacterCover: vi.fn(),
  updateResource: vi.fn(),
  updateVersionVisibility: vi.fn(),
  uploadCharacterCover: vi.fn(),
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
  return render(<MemoryRouter initialEntries={['/lorebooks/lorebook-1/edit']}><Routes>
    <Route path="/lorebooks/:resourceId/edit" element={<><LorebookEditorPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1', username: 'alice' }, isLoading: false })
  getResource.mockReset().mockResolvedValue({
    id: 'lorebook-1',
    authorId: 'author-1',
    resourceType: 'sillytavern/lorebook',
    revision: 'rev-1',
    metadata: {
      name: 'Atlas',
      description: 'World notes',
      language: 'en-uk',
      visibility: 'private',
      tags: ['world'],
    },
  })
  getResourceData.mockReset().mockResolvedValue({
    revision: 'data-1',
    data: { scan_depth: 2, token_budget: 512, recursive_scanning: false, entries: [] },
  })
  listResourceVersions.mockReset().mockResolvedValue([])
  listResources.mockReset().mockResolvedValue({ items: [] })
  updateResource.mockReset().mockResolvedValue({ revision: 'rev-2' })
  saveResourceData.mockReset().mockResolvedValue({ revision: 'data-2', data: { entries: [] } })
})

it('loads lorebook draft data and saves changes', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateResource).toHaveBeenCalledWith(
    'lorebook-1',
    expect.objectContaining({ name: 'Atlas' }),
    'rev-1',
  ))
  await waitFor(() => expect(saveResourceData).toHaveBeenCalledWith(
    'lorebook-1',
    expect.any(Object),
    'data-1',
  ))
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

