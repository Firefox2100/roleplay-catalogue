import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getResource, getResourceData, listResourceVersions, updateResource } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { DshWorldEditorPage } from './DshWorldEditorPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  deleteResource: vi.fn(), draftDownloadUrl: vi.fn(() => '/draft.zip'),
  getResource: vi.fn(), getResourceData: vi.fn(), importDshWorld: vi.fn(),
  listResourceVersions: vi.fn(), publishResource: vi.fn(), updateResource: vi.fn(),
}))
vi.mock('../components/TagEditor.jsx', () => ({ TagEditor: () => <div>tag-editor</div> }))
vi.mock('../components/CoAuthorEditor.jsx', () => ({ CoAuthorEditor: () => <div>coauthors</div> }))

const resource = {
  id: 'world-1', authorId: 'author-1', resourceType: 'dsh-agentic-roleplay/world', revision: 1,
  metadata: { name: 'Catalogue name', description: '', language: 'en-uk', visibility: 'private', tags: [] },
}
const draft = { revision: 0, data: {
  worldId: 'native-id', worldName: 'Native name', description: 'From the package', tags: ['mystery'],
  folderName: 'native-world', authorName: 'Alice', worldVersion: '1.0', byteSize: 1048576,
  files: [{ path: 'native-world/world.json' }],
} }

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1' }, isLoading: false })
  getResource.mockResolvedValue(resource); getResourceData.mockResolvedValue(draft)
  listResourceVersions.mockResolvedValue([]); updateResource.mockResolvedValue(resource)
})

it('shows the native package and can adopt its catalogue metadata', async () => {
  const user = userEvent.setup()
  render(<MemoryRouter initialEntries={['/agentic-worlds/world-1/edit']}><Routes>
    <Route path="/agentic-worlds/:resourceId/edit" element={<DshWorldEditorPage />} />
  </Routes></MemoryRouter>)

  expect(await screen.findByText('native-world')).toBeInTheDocument()
  expect(screen.getByText('Alice')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Use package metadata' }))
  expect(screen.getByLabelText('Name')).toHaveValue('Native name')
  expect(screen.getByLabelText('Description')).toHaveValue('From the package')
})
