import { Outlet } from 'react-router-dom'
import { Footer } from './Footer.jsx'
import { Header } from './Header.jsx'

export function Layout() {
  return (
    <div className="app-shell">
      <Header />
      <main className="page-content"><Outlet /></main>
      <Footer />
    </div>
  )
}
