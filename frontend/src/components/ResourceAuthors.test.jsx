import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ResourceAuthors } from './ResourceAuthors.jsx'

it('renders the author and co-authors when present', () => {
  render(<ResourceAuthors resource={{ authorUsername: 'alice', coAuthorUsernames: ['bob', 'carol'] }} />)
  expect(screen.getByRole('heading', { name: 'Author' })).toBeInTheDocument()
  expect(screen.getByText('alice')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Co-authors' })).toBeInTheDocument()
  expect(screen.getByText('bob, carol')).toBeInTheDocument()
})

it('omits the co-authors section when no co-authors are set', () => {
  render(<ResourceAuthors resource={{ authorUsername: 'alice', coAuthorUsernames: [] }} />)
  expect(screen.getByText('alice')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Co-authors' })).not.toBeInTheDocument()
})
