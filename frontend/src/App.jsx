import { lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { Layout } from './components/Layout.jsx'
import './App.css'

function lazyPage(importer, exportName) {
  return lazy(() => importer().then((module) => ({ default: module[exportName] })))
}

const HomePage = lazyPage(() => import('./pages/HomePage.jsx'), 'HomePage')
const LoginPage = lazyPage(() => import('./pages/LoginPage.jsx'), 'LoginPage')
const RegisterPage = lazyPage(() => import('./pages/RegisterPage.jsx'), 'RegisterPage')
const CreateResourcePage = lazyPage(() => import('./pages/CreateResourcePage.jsx'), 'CreateResourcePage')
const CharacterEditorPage = lazyPage(() => import('./pages/CharacterEditorPage.jsx'), 'CharacterEditorPage')
const MyResourcesPage = lazyPage(() => import('./pages/MyResourcesPage.jsx'), 'MyResourcesPage')
const ImageEditorPage = lazyPage(() => import('./pages/ImageEditorPage.jsx'), 'ImageEditorPage')
const CharacterDetailPage = lazyPage(() => import('./pages/CharacterDetailPage.jsx'), 'CharacterDetailPage')
const ImageDetailPage = lazyPage(() => import('./pages/ImageDetailPage.jsx'), 'ImageDetailPage')
const LorebookEditorPage = lazyPage(() => import('./pages/LorebookEditorPage.jsx'), 'LorebookEditorPage')
const LorebookDetailPage = lazyPage(() => import('./pages/LorebookDetailPage.jsx'), 'LorebookDetailPage')
const ProfilePage = lazyPage(() => import('./pages/ProfilePage.jsx'), 'ProfilePage')
const WorldEditorPage = lazyPage(() => import('./pages/WorldEditorPage.jsx'), 'WorldEditorPage')
const WorldDetailPage = lazyPage(() => import('./pages/WorldDetailPage.jsx'), 'WorldDetailPage')
const PresetEditorPage = lazyPage(() => import('./pages/PresetEditorPage.jsx'), 'PresetEditorPage')
const PresetDetailPage = lazyPage(() => import('./pages/PresetDetailPage.jsx'), 'PresetDetailPage')

function LazyPageOutlet() {
  const { t } = useTranslation()
  return (
    <Suspense fallback={<div className="page-loading" role="status">{t('app.loadingPage')}</div>}>
      <Outlet />
    </Suspense>
  )
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route element={<LazyPageOutlet />}>
            <Route index element={<HomePage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="reset-password" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="resources/new" element={<CreateResourcePage />} />
            <Route path="resources/mine" element={<MyResourcesPage />} />
            <Route path="resources/:resourceId/edit" element={<CharacterEditorPage />} />
            <Route path="images/:resourceId/edit" element={<ImageEditorPage />} />
            <Route path="lorebooks/:resourceId/edit" element={<LorebookEditorPage />} />
            <Route path="worlds/:resourceId/edit" element={<WorldEditorPage />} />
            <Route path="presets/:resourceId/edit" element={<PresetEditorPage />} />
            <Route path="characters/:resourceId" element={<CharacterDetailPage />} />
            <Route path="images/:resourceId" element={<ImageDetailPage />} />
            <Route path="lorebooks/:resourceId" element={<LorebookDetailPage />} />
            <Route path="worlds/:resourceId" element={<WorldDetailPage />} />
            <Route path="presets/:resourceId" element={<PresetDetailPage />} />
            <Route path="*" element={<HomePage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
