import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  getResource, getResourceVersionData, listResourceVersions, resourceImageUrl, versionDownloadUrl,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { WorldDetailPage } from './WorldDetailPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  getResource: vi.fn(),
  getResourceVersionData: vi.fn(),
  listResourceVersions: vi.fn(),
  resourceImageUrl: vi.fn(),
  versionDownloadUrl: vi.fn(),
}))
vi.mock('../components/ResourceImage.jsx', () => ({ ResourceImage: () => <div>image</div> }))
vi.mock('../components/ResourceMetrics.jsx', () => ({ ResourceMetrics: () => <div>metrics</div> }))
vi.mock('../components/ResourceAuthors.jsx', () => ({ ResourceAuthors: () => <div>authors</div> }))
vi.mock('../components/ReleaseDiff.jsx', () => ({ ReleaseDiff: () => <div>diff</div> }))

function renderPage() {
  return render(<MemoryRouter initialEntries={['/worlds/world-1']}><Routes>
    <Route path="/worlds/:resourceId" element={<WorldDetailPage />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'author-1' } })
  getResource.mockReset()
  getResourceVersionData.mockReset()
  listResourceVersions.mockReset()
  resourceImageUrl.mockReset().mockReturnValue('/images/world.png')
  versionDownloadUrl.mockReset().mockReturnValue('/download/version-1')
})

it('loads world details with version data and edit/download actions', async () => {
  getResource.mockResolvedValue({
    id: 'world-1',
    authorId: 'author-1',
    metadata: { name: 'Aether', description: 'A living world', language: 'en-uk', tags: ['fantasy'] },
  })
  listResourceVersions.mockResolvedValue([{ id: 'version-1', version: 'v1.0.0', contentDiff: '@@ test' }])
  getResourceVersionData.mockResolvedValue({
    data: {
      world: { starting_time: '2026-08-20T12:00:00Z' },
      sections: { locations: [{ id: 'loc-1', name: 'Northwatch' }], items: [{ id: 'item-1' }] },
    },
  })

  renderPage()
  expect(await screen.findByRole('heading', { name: 'Aether' })).toBeInTheDocument()
  expect(await screen.findByText('Northwatch')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('href', '/download/version-1')
  expect(screen.getByRole('link', { name: 'Edit world' })).toHaveAttribute('href', '/worlds/world-1/edit')
  expect(screen.getByRole('heading', { name: 'World contents' })).toBeInTheDocument()
})

it('shows a user-facing error when world loading fails', async () => {
  getResource.mockRejectedValue(new Error('offline'))
  listResourceVersions.mockResolvedValue([])
  renderPage()
  expect(await screen.findByText('The world could not be loaded.')).toBeInTheDocument()
})
