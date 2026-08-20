import { act, fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { ResourceImage } from './ResourceImage.jsx'

it('retries a failed image with a cache-busting attempt parameter', async () => {
  vi.useFakeTimers()
  render(<ResourceImage src="/cover.png" alt="Cover" />)
  fireEvent.error(screen.getByRole('img', { name: 'Cover' }))
  await act(() => vi.advanceTimersByTimeAsync(350))
  expect(screen.getByRole('img', { name: 'Cover' })).toHaveAttribute('src', '/cover.png?attempt=1')
  vi.useRealTimers()
})
