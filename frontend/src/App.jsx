import { Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { Layout } from './components/Layout.jsx'
import { HomePage } from './pages/HomePage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { RegisterPage } from './pages/RegisterPage.jsx'
import { CreateResourcePage } from './pages/CreateResourcePage.jsx'
import { CharacterEditorPage } from './pages/CharacterEditorPage.jsx'
import { MyResourcesPage } from './pages/MyResourcesPage.jsx'
import { ImageEditorPage } from './pages/ImageEditorPage.jsx'
import { CharacterDetailPage } from './pages/CharacterDetailPage.jsx'
import { ImageDetailPage } from './pages/ImageDetailPage.jsx'
import { LorebookEditorPage } from './pages/LorebookEditorPage.jsx'
import { LorebookDetailPage } from './pages/LorebookDetailPage.jsx'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="resources/new" element={<CreateResourcePage />} />
          <Route path="resources/mine" element={<MyResourcesPage />} />
          <Route path="resources/:resourceId/edit" element={<CharacterEditorPage />} />
          <Route path="images/:resourceId/edit" element={<ImageEditorPage />} />
          <Route path="lorebooks/:resourceId/edit" element={<LorebookEditorPage />} />
          <Route path="characters/:resourceId" element={<CharacterDetailPage />} />
          <Route path="images/:resourceId" element={<ImageDetailPage />} />
          <Route path="lorebooks/:resourceId" element={<LorebookDetailPage />} />
          <Route path="*" element={<HomePage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
