import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import {
  createSignedDownloadUrl, getResource, listResourceVersions,
} from '../api/resources.js'
import { copyText } from '../utils/clipboard.js'
import { ImageDetailPage } from './ImageDetailPage.jsx'

vi.mock('../api/resources.js', () => ({
  createSignedDownloadUrl: vi.fn(),
  getResource: vi.fn(),
  imageContentUrl: vi.fn((id) => `/api/images/${id}/content`),
  listResourceVersions: vi.fn(),
  versionDownloadUrl: vi.fn((id) => `/api/versions/${id}/download`),
}))
vi.mock('../utils/clipboard.js', () => ({ copyText: vi.fn() }))

const resource = {
  id: 'image-1', resourceType: 'core/image', authorUsername: 'alice', coAuthorUsernames: [],
  authorId: 'author', viewCount: 21, downloadCount: 4,
  metadata: { name: 'Portrait', description: 'A portrait', language: 'en-uk', tags: ['art'] },
}
const version = {
  id: 'version-1', metadata: resource.metadata,
}

beforeEach(() => {
  getResource.mockReset().mockResolvedValue(resource)
  listResourceVersions.mockReset().mockResolvedValue([version])
  createSignedDownloadUrl.mockReset()
  copyText.mockReset()
})

function renderPage() {
  return render(<MemoryRouter initialEntries={['/images/image-1']}><Routes>
    <Route path="/images/:resourceId" element={<ImageDetailPage />} />
  </Routes></MemoryRouter>)
}

it('renders image metadata, counters, and backend download URL', async () => {
  renderPage()
  expect(await screen.findByRole('heading', { name: 'Portrait' })).toBeInTheDocument()
  expect(screen.getByTitle('Views')).toHaveTextContent('21')
  expect(screen.getByTitle('Downloads')).toHaveTextContent('4')
  expect(screen.getByRole('link', { name: 'Download' })).toHaveAttribute(
    'href', '/api/versions/version-1/download',
  )
  expect(screen.getByText('A portrait')).toBeInTheDocument()
})

it('generates and copies a signed download link', async () => {
  createSignedDownloadUrl.mockResolvedValue({ url: 'https://storage.test/signed', expiresIn: 120 })
  copyText.mockResolvedValue()
  const user = userEvent.setup()
  renderPage()
  await screen.findByRole('heading', { name: 'Portrait' })
  await user.click(screen.getByRole('button', { name: 'Copy download link' }))
  expect(copyText).toHaveBeenCalledWith('https://storage.test/signed')
  expect(await screen.findByRole('status')).toHaveTextContent('120 seconds')
})

it('rejects wrong resource types as unavailable', async () => {
  getResource.mockResolvedValue({ ...resource, resourceType: 'sillytavern/character' })
  renderPage()
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded')
})
