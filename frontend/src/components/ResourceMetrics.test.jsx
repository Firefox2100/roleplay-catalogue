import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ResourceMetrics } from './ResourceMetrics.jsx'

it('renders localized view and download totals with accessible labels', () => {
  render(<ResourceMetrics resource={{ viewCount: 1234, downloadCount: 56 }} />)
  const metrics = screen.getByLabelText('Resource engagement')
  expect(metrics).toHaveTextContent(/1,234/)
  expect(screen.getByTitle('Views')).toBeInTheDocument()
  expect(screen.getByTitle('Downloads')).toHaveTextContent('56')
})
