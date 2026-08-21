import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  getResource,
  getResourceData,
  importCharacterCard,
  listResources,
  listResourceVersions,
  saveResourceData,
  updateResource,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { CharacterEditorPage } from './CharacterEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  clearCharacterCover: vi.fn(),
  deleteResource: vi.fn(),
  draftDownloadUrl: vi.fn(() => '/draft/download'),
  getResource: vi.fn(),
  getResourceData: vi.fn(),
  importCharacterCard: vi.fn(),
  listResources: vi.fn(),
  listResourceVersions: vi.fn(),
  publishResource: vi.fn(),
  saveResourceData: vi.fn(),
  selectCharacterCover: vi.fn(),
  updateResource: vi.fn(),
  updateVersionVisibility: vi.fn(),
  uploadCharacterCover: vi.fn(),
}))
vi.mock('../components/TagEditor.jsx', () => ({ TagEditor: () => <div>tag-editor</div> }))
vi.mock('../components/ResourceImage.jsx', () => ({
  ResourceImage: ({ imageResourceId }) => <div data-testid="resource-image">{imageResourceId}</div>,
}))
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
  return render(<MemoryRouter initialEntries={['/resources/character-1/edit']}><Routes>
    <Route path="/resources/:resourceId/edit" element={<><CharacterEditorPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1', username: 'alice' }, isLoading: false })
  getResource.mockReset().mockResolvedValue({
    id: 'character-1',
    authorId: 'author-1',
    resourceType: 'sillytavern/character',
    revision: 'rev-1',
    metadata: {
      name: 'Aster',
      description: 'Helpful character',
      language: 'en-uk',
      visibility: 'private',
      tags: ['fantasy'],
    },
    linkedLorebooks: [],
  })
  getResourceData.mockReset().mockResolvedValue({
    revision: 'data-1',
    data: {
      name: 'Aster',
      tags: [],
      nickname: '',
      alternate_greetings: [],
      group_only_greetings: [],
    },
  })
  listResources.mockReset().mockImplementation(async ({ resourceType }) => {
    if (resourceType === 'core/image') return { items: [] }
    if (resourceType === 'sillytavern/lorebook') {
      return {
        items: [{
          id: 'lorebook-1',
          authorId: 'author-1',
          authorUsername: 'alice',
          draftDataId: 'draft-1',
          metadata: { name: 'Lorebook', description: '' },
        }],
      }
    }
    return { items: [] }
  })
  listResourceVersions.mockReset().mockImplementation(async (id) => {
    if (id === 'character-1') return [{ id: 'version-1', version: 'v1.0.0', versionNumber: 1, visibility: 'private' }]
    if (id === 'lorebook-1') return [{ id: 'lb-version-1', version: 'v1.0.0' }]
    return []
  })
  updateResource.mockReset().mockResolvedValue({ revision: 'rev-2' })
  saveResourceData.mockReset().mockResolvedValue({ revision: 'data-2', data: { name: 'Aster' } })
  importCharacterCard.mockReset()
})

it('loads character draft/editor state and saves draft changes', async () => {
  const user = userEvent.setup()
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Aster' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Linked lorebooks' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateResource).toHaveBeenCalledWith(
    'character-1',
    expect.objectContaining({ name: 'Aster' }),
    'rev-1',
  ))
  await waitFor(() => expect(saveResourceData).toHaveBeenCalledWith(
    'character-1',
    expect.any(Object),
    'data-1',
  ))
})

it('redirects anonymous users to login', () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  renderPage()
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})

it('shows the imported PNG cover and card data without requiring a refresh', async () => {
  importCharacterCard.mockResolvedValue({
    resource: {
      id: 'character-1', authorId: 'author-1', resourceType: 'sillytavern/character',
      revision: 'rev-2', coverImageResourceId: 'imported-cover', linkedLorebooks: [],
      metadata: {
        name: 'Aster', description: 'Imported description', language: 'en-uk',
        visibility: 'private', tags: ['imported'],
      },
    },
    draft: {
      revision: 'data-2',
      data: {
        name: 'Imported Aster', tags: [], nickname: '',
        alternate_greetings: [], group_only_greetings: [],
      },
    },
  })
  const user = userEvent.setup()
  const { container } = renderPage()
  await screen.findByRole('heading', { name: 'Aster' })

  const file = new File(['png'], 'character.png', { type: 'image/png' })
  await user.upload(container.querySelector('input[accept*=".png"]'), file)

  await waitFor(() => expect(importCharacterCard).toHaveBeenCalledWith('character-1', file))
  expect(await screen.findByTestId('resource-image')).toHaveTextContent('imported-cover')
  expect(screen.getByDisplayValue('Imported Aster')).toBeInTheDocument()
  expect(screen.getByDisplayValue('Imported description')).toBeInTheDocument()
})
