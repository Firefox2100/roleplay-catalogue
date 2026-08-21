import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  getResource,
  getResourceData,
  listResourceVersions,
  saveResourceData,
  updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { WorldEditorPage } from './WorldEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  deleteResource: vi.fn(),
  draftDownloadUrl: vi.fn(() => '/draft/download'),
  getResource: vi.fn(),
  getResourceData: vi.fn(),
  importWorldBundle: vi.fn(),
  imageContentUrl: vi.fn(() => '/images/world'),
  listResourceVersions: vi.fn(),
  publishResource: vi.fn(),
  saveResourceData: vi.fn(),
  updateResource: vi.fn(),
}))
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
  return render(<MemoryRouter initialEntries={['/worlds/world-1/edit']}><Routes>
    <Route path="/worlds/:resourceId/edit" element={<><WorldEditorPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1' }, isLoading: false })
  getResource.mockReset().mockResolvedValue({
    id: 'world-1',
    authorId: 'author-1',
    resourceType: 'world-simulation-engine/world',
    revision: 'rev-1',
    metadata: {
      name: 'Aether',
      description: 'Simulation world',
      language: 'en-uk',
      visibility: 'private',
      tags: ['sim'],
    },
  })
  getResourceData.mockReset().mockRejectedValue({ status: 404 })
  listResourceVersions.mockReset().mockResolvedValue([])
  updateResource.mockReset().mockResolvedValue({
    id: 'world-1',
    authorId: 'author-1',
    resourceType: 'world-simulation-engine/world',
    revision: 'rev-2',
    metadata: {
      name: 'Aether',
      description: 'Simulation world',
      language: 'en-uk',
      visibility: 'private',
      tags: ['sim'],
    },
  })
  saveResourceData.mockReset().mockResolvedValue({
    revision: 'data-2',
    data: { world: { name: 'Aether' }, sections: {} },
  })
})

it('initializes a new world draft and saves metadata/data', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Aether' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'World settings' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateResource).toHaveBeenCalledWith(
    'world-1',
    expect.objectContaining({ name: 'Aether' }),
    'rev-1',
  ))
  await waitFor(() => expect(saveResourceData).toHaveBeenCalledWith(
    'world-1',
    expect.any(Object),
    null,
  ))
})

it('shows loading state for anonymous users while auth is unresolved', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByText('Loading world…')).toBeInTheDocument()
})
