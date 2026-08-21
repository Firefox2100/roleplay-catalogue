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
import { PresetEditorPage } from './PresetEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  deleteResource: vi.fn(),
  draftDownloadUrl: vi.fn(() => '/draft/download'),
  getResource: vi.fn(),
  getResourceData: vi.fn(),
  importPreset: vi.fn(),
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
  return render(<MemoryRouter initialEntries={['/presets/preset-1/edit']}><Routes>
    <Route path="/presets/:resourceId/edit" element={<><PresetEditorPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1' }, isLoading: false })
  getResource.mockReset().mockResolvedValue({
    id: 'preset-1',
    authorId: 'author-1',
    resourceType: 'sillytavern/preset',
    revision: 'rev-1',
    metadata: {
      name: 'Balanced Preset',
      description: 'General chat preset',
      language: 'en-uk',
      visibility: 'private',
      tags: ['chat'],
    },
  })
  listResourceVersions.mockReset().mockResolvedValue([])
  getResourceData.mockReset().mockResolvedValue({
    revision: 'data-1',
    data: { prompts: [], prompt_order: [{ character_id: 100000, order: [] }] },
  })
  updateResource.mockReset().mockResolvedValue({ revision: 'rev-2' })
  saveResourceData.mockReset().mockResolvedValue({ revision: 'data-2', data: { prompts: [] } })
})

it('loads preset draft data and saves edits', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Balanced Preset' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateResource).toHaveBeenCalledWith(
    'preset-1',
    expect.objectContaining({ name: 'Balanced Preset' }),
    'rev-1',
  ))
  await waitFor(() => expect(saveResourceData).toHaveBeenCalledWith(
    'preset-1',
    expect.any(Object),
    'data-1',
  ))
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

