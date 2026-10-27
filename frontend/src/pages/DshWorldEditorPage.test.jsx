import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  getResource, getResourceData, importDshWorld, listResourceVersions, publishResource,
  updateResource,
} from '../api/resources.js'
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
  getResource.mockReset().mockResolvedValue(resource)
  getResourceData.mockReset().mockResolvedValue(draft)
  listResourceVersions.mockReset().mockResolvedValue([])
  updateResource.mockReset().mockResolvedValue(resource)
  importDshWorld.mockReset()
  publishResource.mockReset()
})

function renderPage() {
  return render(<MemoryRouter initialEntries={['/agentic-worlds/world-1/edit']}><Routes>
    <Route path="/agentic-worlds/:resourceId/edit" element={<DshWorldEditorPage />} />
    <Route path="/login" element={<div>login destination</div>} />
  </Routes></MemoryRouter>)
}

it('shows the native package and can adopt its catalogue metadata', async () => {
  const user = userEvent.setup()
  renderPage()

  expect(await screen.findByText('native-world')).toBeInTheDocument()
  expect(screen.getByText('Alice')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Use package metadata' }))
  expect(screen.getByLabelText('Name')).toHaveValue('Native name')
  expect(screen.getByLabelText('Description')).toHaveValue('From the package')
})

it('saves edited catalogue metadata', async () => {
  const user = userEvent.setup()
  renderPage()
  const name = await screen.findByLabelText('Name')
  await user.clear(name)
  await user.type(name, 'Updated world')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateResource).toHaveBeenCalledWith(
    'world-1', expect.objectContaining({ name: 'Updated world' }), 1,
  ))
  expect(await screen.findByRole('status')).toHaveTextContent('saved')
})

it('imports a replacement package and publishes it', async () => {
  const importedDraft = { ...draft, data: { ...draft.data, worldName: 'Imported world' } }
  importDshWorld.mockResolvedValue({ resource, draft: importedDraft })
  publishResource.mockResolvedValue({ id: 'version-1', version: 'v1.0.0' })
  const user = userEvent.setup()
  const { container } = renderPage()
  await screen.findByText('native-world')

  await user.upload(container.querySelector('input[type="file"]'), new File(['zip'], 'world.zip', {
    type: 'application/zip',
  }))
  await waitFor(() => expect(importDshWorld).toHaveBeenCalledWith('world-1', expect.any(File)))
  expect(await screen.findByText('Imported world')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Publish' }))
  await waitFor(() => expect(publishResource).toHaveBeenCalledWith('world-1', 'v1.0.0'))
  expect(await screen.findByText('v1.0.0')).toBeInTheDocument()
})

it('shows import and save failures', async () => {
  updateResource.mockRejectedValue(new Error('save failed'))
  importDshWorld.mockRejectedValue(new Error('invalid archive'))
  const user = userEvent.setup()
  const { container } = renderPage()
  await screen.findByText('native-world')

  await user.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('save')
  await user.upload(container.querySelector('input[type="file"]'), new File(['bad'], 'bad.zip'))
  expect(await screen.findByRole('alert')).toHaveTextContent('invalid archive')
})

it('redirects anonymous users and reports invalid resources', async () => {
  useAuth.mockReturnValue({ user: null, isLoading: false })
  const { unmount } = renderPage()
  expect(screen.getByText('login destination')).toBeInTheDocument()
  unmount()

  useAuth.mockReturnValue({ user: { id: 'author-1' }, isLoading: false })
  getResource.mockResolvedValue({ ...resource, resourceType: 'sillytavern/character' })
  renderPage()
  expect(await screen.findByRole('alert')).toHaveTextContent('load')
})
