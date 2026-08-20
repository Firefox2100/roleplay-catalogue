import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { addCoAuthor, getResource, removeCoAuthor } from '../api/resources.js'
import { CoAuthorEditor } from './CoAuthorEditor.jsx'

vi.mock('../api/resources.js', () => ({
  addCoAuthor: vi.fn(),
  getResource: vi.fn(),
  removeCoAuthor: vi.fn(),
}))

beforeEach(() => {
  addCoAuthor.mockReset()
  getResource.mockReset()
  removeCoAuthor.mockReset()
})

it('loads co-authors and lets the owner add and remove them', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  getResource
    .mockResolvedValueOnce({ coAuthorIds: ['u2'], coAuthorUsernames: ['bob'] })
    .mockResolvedValueOnce({ coAuthorIds: ['u2', 'u3'], coAuthorUsernames: ['bob', 'charlie'] })
    .mockResolvedValueOnce({ coAuthorIds: ['u3'], coAuthorUsernames: ['charlie'] })
  addCoAuthor.mockResolvedValue({})
  removeCoAuthor.mockResolvedValue({})

  render(<CoAuthorEditor resourceId="resource-1" authorId="owner-1" currentUserId="owner-1" onChange={onChange} />)

  expect(await screen.findByText('bob')).toBeInTheDocument()
  await user.type(screen.getByPlaceholderText('Username'), 'charlie')
  await user.click(screen.getByRole('button', { name: 'Add' }))
  await waitFor(() => expect(addCoAuthor).toHaveBeenCalledWith('resource-1', 'charlie'))
  expect(await screen.findByText('charlie')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Remove bob' }))
  await waitFor(() => expect(removeCoAuthor).toHaveBeenCalledWith('resource-1', 'u2'))
  await waitFor(() => expect(screen.queryByText('bob')).not.toBeInTheDocument())
  expect(onChange).toHaveBeenCalled()
})

it('hides itself for non-owners when no co-authors exist', async () => {
  getResource.mockResolvedValue({ coAuthorIds: [], coAuthorUsernames: [] })
  render(<CoAuthorEditor resourceId="resource-2" authorId="owner-1" currentUserId="viewer-1" />)
  await waitFor(() => expect(screen.queryByText('Co-authors')).not.toBeInTheDocument())
})
