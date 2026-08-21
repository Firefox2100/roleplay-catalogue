import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import App from './App.jsx'

vi.mock('./auth/AuthProvider.jsx', () => ({ AuthProvider: ({ children }) => children }))
vi.mock('./components/Layout.jsx', () => ({
  Layout: () => <main><span>layout</span><MockOutlet /></main>,
}))

import { Outlet } from 'react-router-dom'
function MockOutlet() { return <Outlet /> }

vi.mock('./pages/HomePage.jsx', () => ({ HomePage: () => <div>home</div> }))
vi.mock('./pages/LoginPage.jsx', () => ({ LoginPage: () => <div>login</div> }))
vi.mock('./pages/RegisterPage.jsx', () => ({ RegisterPage: () => <div>register</div> }))
vi.mock('./pages/ProfilePage.jsx', () => ({ ProfilePage: () => <div>profile</div> }))
vi.mock('./pages/CreateResourcePage.jsx', () => ({ CreateResourcePage: () => <div>create</div> }))
vi.mock('./pages/MyResourcesPage.jsx', () => ({ MyResourcesPage: () => <div>mine</div> }))
vi.mock('./pages/CharacterEditorPage.jsx', () => ({ CharacterEditorPage: () => <div>character-editor</div> }))
vi.mock('./pages/ImageEditorPage.jsx', () => ({ ImageEditorPage: () => <div>image-editor</div> }))
vi.mock('./pages/LorebookEditorPage.jsx', () => ({ LorebookEditorPage: () => <div>lorebook-editor</div> }))
vi.mock('./pages/WorldEditorPage.jsx', () => ({ WorldEditorPage: () => <div>world-editor</div> }))
vi.mock('./pages/PresetEditorPage.jsx', () => ({ PresetEditorPage: () => <div>preset-editor</div> }))
vi.mock('./pages/CharacterDetailPage.jsx', () => ({ CharacterDetailPage: () => <div>character-detail</div> }))
vi.mock('./pages/ImageDetailPage.jsx', () => ({ ImageDetailPage: () => <div>image-detail</div> }))
vi.mock('./pages/LorebookDetailPage.jsx', () => ({ LorebookDetailPage: () => <div>lorebook-detail</div> }))
vi.mock('./pages/WorldDetailPage.jsx', () => ({ WorldDetailPage: () => <div>world-detail</div> }))
vi.mock('./pages/PresetDetailPage.jsx', () => ({ PresetDetailPage: () => <div>preset-detail</div> }))

describe('App routes', () => {
  it.each([
    ['/', 'home'], ['/login', 'login'], ['/reset-password', 'login'], ['/register', 'register'],
    ['/profile', 'profile'], ['/resources/new', 'create'], ['/resources/mine', 'mine'],
    ['/resources/1/edit', 'character-editor'], ['/images/1/edit', 'image-editor'],
    ['/lorebooks/1/edit', 'lorebook-editor'], ['/worlds/1/edit', 'world-editor'],
    ['/presets/1/edit', 'preset-editor'], ['/characters/1', 'character-detail'],
    ['/images/1', 'image-detail'], ['/lorebooks/1', 'lorebook-detail'],
    ['/worlds/1', 'world-detail'], ['/presets/1', 'preset-detail'], ['/unknown', 'home'],
  ])('renders %s through the shared layout', (path, expected) => {
    render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
    expect(screen.getByText('layout')).toBeInTheDocument()
    expect(screen.getByText(expected)).toBeInTheDocument()
  })
})
