import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getResource, getResourceVersionData, listResourceVersions, versionDownloadUrl } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { PresetDetailPage } from './PresetDetailPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  getResource: vi.fn(),
  getResourceVersionData: vi.fn(),
  listResourceVersions: vi.fn(),
  versionDownloadUrl: vi.fn(),
}))
vi.mock('../components/ResourceMetrics.jsx', () => ({ ResourceMetrics: () => <div>metrics</div> }))
vi.mock('../components/ResourceAuthors.jsx', () => ({ ResourceAuthors: () => <div>authors</div> }))
vi.mock('../components/ReleaseDiff.jsx', () => ({ ReleaseDiff: () => <div>diff</div> }))

function renderPage() {
  return render(<MemoryRouter initialEntries={['/presets/resource-1']}><Routes>
    <Route path="/presets/:resourceId" element={<PresetDetailPage />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1' } })
  getResource.mockReset()
  getResourceVersionData.mockReset()
  listResourceVersions.mockReset()
  versionDownloadUrl.mockReset().mockReturnValue('/download/version-1')
})

it('loads preset metadata, prompts, and owner actions', async () => {
  getResource.mockResolvedValue({
    id: 'resource-1',
    authorId: 'author-1',
    resourceType: 'sillytavern/preset',
    metadata: { name: 'Balanced Chat', description: 'General preset', tags: ['chat'] },
  })
  listResourceVersions.mockResolvedValue([
    { id: 'version-1', version: 'v1.0.0', contentDiff: '@@ diff' },
    { id: 'version-2', version: 'v1.1.0', contentDiff: '@@ diff' },
  ])
  getResourceVersionData.mockResolvedValue({
    data: {
      temperature: 1,
      top_p: 0.95,
      top_k: 40,
      min_p: 0.05,
      repetition_penalty: 1.1,
      openai_max_context: 8192,
      openai_max_tokens: 512,
      prompts: [{ identifier: 'main', name: 'Main prompt', role: 'system', marker: false, content: 'Stay in character.' }],
    },
  })

  renderPage()
  expect(await screen.findByRole('heading', { name: 'Balanced Chat' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('href', '/download/version-1')
  expect(screen.getByRole('link', { name: 'Edit preset' })).toHaveAttribute('href', '/presets/resource-1/edit')
  expect(screen.getByText('Main prompt')).toBeInTheDocument()
  expect(screen.getByText('Stay in character.')).toBeInTheDocument()
})

it('switches versions and refetches preset data', async () => {
  getResource.mockResolvedValue({
    id: 'resource-1',
    authorId: 'author-1',
    resourceType: 'sillytavern/preset',
    metadata: { name: 'Balanced Chat', description: 'General preset', tags: ['chat'] },
  })
  listResourceVersions.mockResolvedValue([
    { id: 'version-1', version: 'v1.0.0', contentDiff: '@@ first' },
    { id: 'version-2', version: 'v1.1.0', contentDiff: '@@ second' },
  ])
  getResourceVersionData
    .mockResolvedValueOnce({
      data: {
        temperature: 1, top_p: 0.95, top_k: 40, min_p: 0.05, repetition_penalty: 1.1,
        openai_max_context: 8192, openai_max_tokens: 512,
        prompts: [{ identifier: 'one', name: 'V1 prompt', role: 'system', marker: false, content: 'v1' }],
      },
    })
    .mockResolvedValueOnce({
      data: {
        temperature: 0.8, top_p: 0.9, top_k: 30, min_p: 0.04, repetition_penalty: 1.05,
        openai_max_context: 4096, openai_max_tokens: 256,
        prompts: [{ identifier: 'two', name: 'V2 prompt', role: 'system', marker: false, content: 'v2' }],
      },
    })
  const user = userEvent.setup()

  renderPage()
  expect(await screen.findByText('V1 prompt')).toBeInTheDocument()
  await user.selectOptions(screen.getByRole('combobox'), 'version-2')
  expect(await screen.findByText('V2 prompt')).toBeInTheDocument()
  expect(getResourceVersionData).toHaveBeenCalledWith('version-2')
})
