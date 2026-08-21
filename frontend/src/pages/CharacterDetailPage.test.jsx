import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  createSignedDownloadUrl,
  forkResourceVersion,
  getResource,
  getResourceVersionData,
  listResourceVersions,
  versionCoverUrl,
  versionDownloadUrl,
} from '../api/resources.js'
import { useAuth } from '../auth/useAuth.js'
import { copyText } from '../utils/clipboard.js'
import { CharacterDetailPage } from './CharacterDetailPage.jsx'

vi.mock('../auth/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../api/resources.js', () => ({
  createSignedDownloadUrl: vi.fn(),
  forkResourceVersion: vi.fn(),
  getResource: vi.fn(),
  getResourceVersionData: vi.fn(),
  listResourceVersions: vi.fn(),
  versionCoverUrl: vi.fn(),
  versionDownloadUrl: vi.fn(),
}))
vi.mock('../utils/clipboard.js', () => ({ copyText: vi.fn() }))
vi.mock('../components/ResourceImage.jsx', () => ({ ResourceImage: () => <div>image</div> }))
vi.mock('../components/ResourceMetrics.jsx', () => ({ ResourceMetrics: () => <div>metrics</div> }))
vi.mock('../components/ResourceAuthors.jsx', () => ({ ResourceAuthors: () => <div>authors</div> }))
vi.mock('../components/ReleaseDiff.jsx', () => ({ ReleaseDiff: () => <div>diff</div> }))

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}

function renderPage(path = '/characters/resource-1') {
  return render(<MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/characters/:resourceId" element={<><CharacterDetailPage /><Location /></>} />
    <Route path="*" element={<Location />} />
  </Routes></MemoryRouter>)
}

beforeEach(() => {
  useAuth.mockReturnValue({ user: { id: 'user-1' } })
  createSignedDownloadUrl.mockReset()
  forkResourceVersion.mockReset()
  getResource.mockReset()
  getResourceVersionData.mockReset()
  listResourceVersions.mockReset()
  versionCoverUrl.mockReset().mockReturnValue('/covers/version-1')
  versionDownloadUrl.mockReset().mockReturnValue('/download/version-1')
  copyText.mockReset()
})

it('loads a published character, copies a signed link, and forks to the editor', async () => {
  getResource.mockResolvedValue({
    id: 'resource-1',
    resourceType: 'sillytavern/character',
    metadata: { name: 'Aster' },
  })
  listResourceVersions.mockResolvedValue([{
    id: 'version-1',
    version: 'v1.0.0',
    publishedAt: '2026-08-20T12:00:00Z',
    metadata: { name: 'Aster', tags: ['fantasy'], language: 'en-uk' },
    contentDiff: '@@ section',
  }])
  getResourceVersionData.mockResolvedValue({ data: { name: 'Aster', personality: 'Kind' } })
  createSignedDownloadUrl.mockResolvedValue({ url: 'https://example/link', expiresIn: 60 })
  forkResourceVersion.mockResolvedValue({ id: 'fork-1' })
  const user = userEvent.setup()

  renderPage()
  expect(await screen.findByRole('heading', { name: 'Aster' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('href', '/download/version-1')

  await user.click(screen.getByRole('button', { name: 'Copy download link' }))
  await waitFor(() => expect(copyText).toHaveBeenCalledWith('https://example/link'))
  expect(await screen.findByRole('status')).toHaveTextContent('expires in 60')

  await user.click(screen.getByRole('button', { name: 'Fork' }))
  expect(await screen.findByTestId('location')).toHaveTextContent('/resources/fork-1/edit')
})

it('redirects anonymous users to login when forking', async () => {
  useAuth.mockReturnValue({ user: null })
  getResource.mockResolvedValue({
    id: 'resource-1',
    resourceType: 'sillytavern/character',
    metadata: { name: 'Aster' },
  })
  listResourceVersions.mockResolvedValue([{
    id: 'version-1',
    version: 'v1.0.0',
    publishedAt: '2026-08-20T12:00:00Z',
    metadata: { name: 'Aster', tags: [], language: 'en-uk' },
    contentDiff: '',
  }])
  getResourceVersionData.mockResolvedValue({ data: { name: 'Aster' } })
  const user = userEvent.setup()

  renderPage()
  await screen.findByRole('heading', { name: 'Aster' })
  await user.click(screen.getByRole('button', { name: 'Fork' }))
  expect(screen.getByTestId('location')).toHaveTextContent('/login')
})
