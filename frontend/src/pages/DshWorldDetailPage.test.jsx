import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { getResource, getResourceVersionData, listResourceVersions } from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { DshWorldDetailPage } from './DshWorldDetailPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  forkResourceVersion: vi.fn(), getResource: vi.fn(), getResourceVersionData: vi.fn(),
  listResourceVersions: vi.fn(), versionDownloadUrl: vi.fn(() => '/world.zip'),
}))
vi.mock('../components/ResourceMetrics.jsx', () => ({ ResourceMetrics: () => <div>metrics</div> }))
vi.mock('../components/ResourceAuthors.jsx', () => ({ ResourceAuthors: () => <div>authors</div> }))
vi.mock('../components/ReleaseDiff.jsx', () => ({ ReleaseDiff: () => <div>diff</div> }))

beforeEach(() => {
  useAuth.mockReturnValue({ user: null })
  getResource.mockResolvedValue({ id: 'world-1', authorId: 'author-1', resourceType: 'dsh-agentic-roleplay/world', metadata: { name: 'Harbour', description: 'Fog', tags: [] } })
  listResourceVersions.mockResolvedValue([{ id: 'version-1', version: '1.0' }])
  getResourceVersionData.mockResolvedValue({ data: { worldName: 'Harbour', folderName: 'harbour', authorName: 'Alice', worldVersion: '1.0', byteSize: 100, files: [] } })
})

it('offers install guidance, download, and forking', async () => {
  render(<MemoryRouter initialEntries={['/agentic-worlds/world-1']}><Routes>
    <Route path="/agentic-worlds/:resourceId" element={<DshWorldDetailPage />} />
  </Routes></MemoryRouter>)
  expect(await screen.findByRole('heading', { name: 'Harbour' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('href', '/world.zip')
  expect(screen.getByRole('button', { name: 'Fork' })).toBeInTheDocument()
  expect(screen.getByText('harbour')).toBeInTheDocument()
})
