import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ReleaseDiff } from './ReleaseDiff.jsx'

it('summarizes additions and deletions and styles diff lines', () => {
  render(<ReleaseDiff diff={'--- old\n+++ new\n unchanged\n-added\n+added\n@@ section'} />)
  expect(screen.getByText('+1')).toBeInTheDocument()
  expect(screen.getByText('−1')).toBeInTheDocument()
  expect(screen.getByText('+added')).toHaveClass('diff-add')
  expect(screen.getByText('-added')).toHaveClass('diff-remove')
})

it('renders nothing when no diff exists', () => {
  const { container } = render(<ReleaseDiff diff={null} />)
  expect(container).toBeEmptyDOMElement()
})
