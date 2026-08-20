import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { suggestResourceTags } from '../api/resources.js'
import { TagEditor } from './TagEditor.jsx'

vi.mock('../api/resources.js', () => ({ suggestResourceTags: vi.fn() }))

beforeEach(() => suggestResourceTags.mockReset())

it('creates, deduplicates, removes, and backspaces tags', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  const { rerender } = render(<TagEditor id="tags" value={[]} onChange={onChange} />)
  const input = screen.getByRole('textbox')
  await user.type(input, 'Fantasy{Enter}')
  expect(onChange).toHaveBeenCalledWith(['Fantasy'])

  rerender(<TagEditor id="tags" value={['Fantasy']} onChange={onChange} />)
  await user.type(input, 'fantasy{Enter}')
  expect(onChange).toHaveBeenCalledTimes(1)
  await user.clear(input)
  await user.type(input, '{Backspace}')
  expect(onChange).toHaveBeenLastCalledWith([])
  await user.click(screen.getByRole('button', { name: 'Remove Fantasy' }))
  expect(onChange).toHaveBeenLastCalledWith([])
})

it('debounces suggestions and accepts an existing tag when creation is disabled', async () => {
  vi.useFakeTimers()
  const onChange = vi.fn()
  suggestResourceTags.mockResolvedValue(['fantasy', 'science fiction'])
  render(<TagEditor id="tags" value={[]} onChange={onChange} allowCreate={false} />)
  const input = screen.getByRole('textbox')
  fireEvent.focus(input)
  fireEvent.change(input, { target: { value: 'fantasy' } })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(150)
  })
  expect(screen.getByRole('option', { name: 'fantasy' })).toBeInTheDocument()
  fireEvent.keyDown(input, { key: 'Enter' })
  expect(onChange).toHaveBeenCalledWith(['fantasy'])
  vi.useRealTimers()
})

it('loads and adds popular tags', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  suggestResourceTags.mockResolvedValue(['popular'])
  render(<TagEditor id="tags" value={[]} onChange={onChange} showPopular />)
  await user.click(await screen.findByRole('button', { name: 'popular' }))
  expect(suggestResourceTags).toHaveBeenCalledWith('', 5)
  expect(onChange).toHaveBeenCalledWith(['popular'])
})
