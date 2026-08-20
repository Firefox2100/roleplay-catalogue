import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ConflictResolutionModal } from './ConflictResolutionModal.jsx'

it('lets the user choose remote values and applies a resolved payload', async () => {
  const user = userEvent.setup()
  const onApply = vi.fn()
  render(<ConflictResolutionModal
    conflicts={{ name: { base: 'Base', local: 'Mine', remote: 'Theirs' } }}
    merged={{ name: 'Mine', description: 'Already merged' }}
    onApply={onApply} onCancel={vi.fn()} isRetrying={false} />)

  await user.click(screen.getByText('Use theirs'))
  await user.click(screen.getByRole('button', { name: 'Apply & retry save' }))
  expect(onApply).toHaveBeenCalledWith({ name: 'Theirs', description: 'Already merged' })
})

it('keeps keyed-array local defaults and blocks cancellation while retrying', async () => {
  const user = userEvent.setup()
  const onApply = vi.fn()
  const onCancel = vi.fn()
  render(<ConflictResolutionModal
    conflicts={{ entries: { entries: { one: { local: {}, remote: {} } } } }}
    merged={{ entries: [{ uid: 'one', text: 'mine' }] }}
    onApply={onApply} onCancel={onCancel} isRetrying />)
  expect(screen.getByText(/1 entries were changed/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Retrying…' }))
  expect(onApply).not.toHaveBeenCalled()
})
