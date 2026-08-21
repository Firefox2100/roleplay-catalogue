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
import { LorebookDetailPage } from './LorebookDetailPage.jsx'

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

function renderPage(path = '/lorebooks/resource-1?version=version-2') {
  return render(<MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/lorebooks/:resourceId" element={<><LorebookDetailPage /><Location /></>} />
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
  versionCoverUrl.mockReset().mockReturnValue('/covers/version-2')
  versionDownloadUrl.mockReset().mockReturnValue('/download/version-2')
  copyText.mockReset()
})

it('loads the requested lorebook version and handles copy/fork actions', async () => {
  getResource.mockResolvedValue({
    id: 'resource-1',
    resourceType: 'sillytavern/lorebook',
    metadata: { name: 'Atlas' },
  })
  listResourceVersions.mockResolvedValue([
    { id: 'version-1', version: 'v1.0.0', publishedAt: '2026-08-01T12:00:00Z', metadata: { name: 'Atlas', language: 'en-uk', tags: [] } },
    { id: 'version-2', version: 'v1.1.0', publishedAt: '2026-08-20T12:00:00Z', metadata: { name: 'Atlas', language: 'en-uk', tags: ['world'] } },
  ])
  getResourceVersionData.mockResolvedValue({ data: { scan_depth: 2, token_budget: 512, entries: [{ id: 'entry-1', name: 'Northwatch' }] } })
  createSignedDownloadUrl.mockResolvedValue({ url: 'https://example/lorebook', expiresIn: 90 })
  forkResourceVersion.mockResolvedValue({ id: 'fork-lorebook' })
  const user = userEvent.setup()

  renderPage()
  expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute('href', '/download/version-2')
  expect(await screen.findByText('Northwatch')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Copy download link' }))
  await waitFor(() => expect(copyText).toHaveBeenCalledWith('https://example/lorebook'))

  await user.click(screen.getByRole('button', { name: 'Fork' }))
  expect(await screen.findByTestId('location')).toHaveTextContent('/lorebooks/fork-lorebook/edit')
})

it('shows a translated load error when lorebook loading fails', async () => {
  getResource.mockRejectedValue(new Error('offline'))
  listResourceVersions.mockResolvedValue([])
  renderPage('/lorebooks/resource-1')
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded')
})
