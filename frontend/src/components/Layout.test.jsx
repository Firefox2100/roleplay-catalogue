import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { Layout } from './Layout.jsx'

vi.mock('./Header.jsx', () => ({ Header: () => <header>catalogue header</header> }))

it('wraps routed content with the shared header and footer', () => {
  render(<MemoryRouter initialEntries={['/test']}><Routes>
    <Route element={<Layout />}><Route path="/test" element={<p>page content</p>} /></Route>
  </Routes></MemoryRouter>)

  expect(screen.getByRole('banner')).toHaveTextContent('catalogue header')
  expect(screen.getByRole('main')).toHaveTextContent('page content')
  expect(screen.getByRole('contentinfo')).toHaveTextContent(new Date().getFullYear().toString())
})
