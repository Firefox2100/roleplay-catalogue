import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const LOCALE_STORAGE_KEY = 'roleplay-catalogue.locale'
const ENGLISH = 'en-UK'
const CHINESE = 'zh-CN'
const translations = {
  [ENGLISH]: { translation: {
    app: { title: 'Roleplay Catalogue', tagline: 'Create, version and share', homeLabel: 'Roleplay Catalogue home' },
    nav: { primary: 'Primary navigation', home: 'Home', new: 'New' },
    home: { label: 'Home' },
    auth: {
      login: 'Log in', logout: 'Log out', loggingOut: 'Logging out…', loggingIn: 'Logging in…',
      checkingSession: 'Checking sign-in status', welcomeBack: 'Welcome back',
      loginTitle: 'Log in to your account',
      loginDescription: 'Continue building and publishing your roleplay resources.',
      username: 'Username', password: 'Password',
      invalidCredentials: 'The username or password is incorrect.',
      loginFailed: 'Login failed. Please try again.',
      register: 'Create account', registering: 'Creating account…', email: 'Email address',
      noAccount: 'New to the catalogue?', createAccount: 'Create an account',
      alreadyAccount: 'Already have an account?', joinCatalogue: 'Join the catalogue',
      registerTitle: 'Create your account',
      registerDescription: 'Start creating and publishing versioned roleplay resources.',
      passwordHelp: 'Use at least 8 characters.',
      accountExists: 'That username or email address is already registered.',
      registrationFailed: 'Registration failed. Please try again.',
      registrationComplete: 'Almost there', checkEmailTitle: 'Check your email',
      checkEmailDescription: 'We sent an activation link to {{email}}. Activate your account before logging in.',
      backToLogin: 'Back to login',
      activationSuccess: 'Your account is active. You can now log in.',
      activationInvalid: 'This activation link is invalid or has expired.',
    },
    resource: {
      newLabel: 'New resource', createTitle: 'Create New Resource',
      createDescription: 'Create the catalogue entry first. You can add its actual content afterward.',
      name: 'Name', type: 'Resource type', description: 'Description', visibility: 'Visibility',
      tags: 'Tags', tagsPlaceholder: 'fantasy, original character, adventure',
      tagsHelp: 'Separate tags with commas.', create: 'Create resource', creating: 'Creating…',
      createFailed: 'The resource could not be created. Please try again.',
      sessionExpired: 'Your session has expired. Please log in again.',
      createdLabel: 'Resource created', createdTitle: 'Ready for content',
      createdDescription: '“{{name}}” now has its own catalogue identity. Its content can be added next.',
      resourceId: 'Resource ID', createAnother: 'Create another',
      types: {
        'sillytavern/character': 'SillyTavern character (V3)',
        'sillytavern/lorebook': 'SillyTavern lorebook',
        'core/image': 'Image',
      },
      typeHelp: {
        'sillytavern/character': 'A canonical V3 character card. V2 cards can be imported later.',
        'sillytavern/lorebook': 'A standalone SillyTavern lorebook, managed separately from characters.',
        'core/image': 'An immutable image asset; the file will be attached afterward.',
      },
      visibilities: { private: 'Private', authenticated: 'Logged-in users', public: 'Public' },
      visibilityHelp: {
        private: 'Only you can discover and access this resource.',
        authenticated: 'Any logged-in user can discover and access this resource.',
        public: 'Anyone can discover and access this resource.',
      },
    },
    footer: { project: 'Roleplay Catalogue', copyright: '© {{year}}' },
  } },
  [CHINESE]: { translation: {
    app: { title: '角色扮演资源库', tagline: '创作、版本管理与分享', homeLabel: '角色扮演资源库首页' },
    nav: { primary: '主导航', home: '首页', new: '新建' },
    home: { label: '首页' },
    auth: {
      login: '登录', logout: '退出登录', loggingOut: '正在退出…', loggingIn: '正在登录…',
      checkingSession: '正在检查登录状态', welcomeBack: '欢迎回来', loginTitle: '登录你的账户',
      loginDescription: '继续创作并发布你的角色扮演资源。', username: '用户名', password: '密码',
      invalidCredentials: '用户名或密码不正确。', loginFailed: '登录失败，请重试。',
      register: '创建账户', registering: '正在创建账户…', email: '电子邮箱',
      noAccount: '还没有账户？', createAccount: '创建账户', alreadyAccount: '已有账户？',
      joinCatalogue: '加入资源库', registerTitle: '创建你的账户',
      registerDescription: '开始创作并发布带版本管理的角色扮演资源。',
      passwordHelp: '密码至少需要 8 个字符。',
      accountExists: '该用户名或邮箱已被注册。', registrationFailed: '注册失败，请重试。',
      registrationComplete: '即将完成', checkEmailTitle: '请查收邮件',
      checkEmailDescription: '激活链接已发送至 {{email}}。请先激活账户，然后再登录。',
      backToLogin: '返回登录', activationSuccess: '账户已激活，现在可以登录。',
      activationInvalid: '该激活链接无效或已过期。',
    },
    resource: {
      newLabel: '新资源', createTitle: '创建新资源',
      createDescription: '先创建资源的目录条目，之后再添加实际内容。',
      name: '名称', type: '资源类型', description: '描述', visibility: '可见范围',
      tags: '标签', tagsPlaceholder: '奇幻, 原创角色, 冒险', tagsHelp: '请使用逗号分隔标签。',
      create: '创建资源', creating: '正在创建…', createFailed: '无法创建资源，请重试。',
      sessionExpired: '登录状态已过期，请重新登录。', createdLabel: '资源已创建',
      createdTitle: '可以添加内容了', createdDescription: '“{{name}}”现在拥有独立的目录身份，接下来可以添加实际内容。',
      resourceId: '资源 ID', createAnother: '继续创建',
      types: {
        'sillytavern/character': 'SillyTavern 角色卡（V3）',
        'sillytavern/lorebook': 'SillyTavern 世界书',
        'core/image': '图片',
      },
      typeHelp: {
        'sillytavern/character': '规范的 V3 角色卡；之后可以导入 V2 卡片。',
        'sillytavern/lorebook': '独立管理的 SillyTavern 世界书，与角色卡分开。',
        'core/image': '不可变的图片资源；文件将在之后添加。',
      },
      visibilities: { private: '仅自己', authenticated: '已登录用户', public: '公开' },
      visibilityHelp: {
        private: '只有你可以发现和访问此资源。',
        authenticated: '任何已登录用户都可以发现和访问此资源。',
        public: '任何人都可以发现和访问此资源。',
      },
    },
    footer: { project: '角色扮演资源库', copyright: '© {{year}}' },
  } },
}

function getInitialLocale() {
  const storedLocale = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (storedLocale === ENGLISH || storedLocale === CHINESE) return storedLocale
  return navigator.language?.toLowerCase().startsWith('zh') ? CHINESE : ENGLISH
}

const initialLocale = getInitialLocale()
localStorage.setItem(LOCALE_STORAGE_KEY, initialLocale)
document.documentElement.lang = initialLocale
const i18nLocale = initialLocale === CHINESE ? 'zh' : 'en'

i18n.use(initReactI18next).init({
  resources: {
    en: translations[ENGLISH],
    zh: translations[CHINESE],
  },
  lng: i18nLocale,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (locale) => {
  const supportedLocale = locale.startsWith('zh') ? CHINESE : ENGLISH
  localStorage.setItem(LOCALE_STORAGE_KEY, supportedLocale)
  document.documentElement.lang = supportedLocale
})

export default i18n
