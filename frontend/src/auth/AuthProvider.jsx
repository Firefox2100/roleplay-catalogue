import { useCallback, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth.js'
import { AuthContext } from './AuthContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    authApi.getCurrentUser()
      .then((currentUser) => { if (active) setUser(currentUser) })
      .catch(() => { if (active) setUser(null) })
      .finally(() => { if (active) setIsLoading(false) })
    return () => { active = false }
  }, [])

  const login = useCallback(async (username, password) => {
    const currentUser = await authApi.login(username, password)
    setUser(currentUser)
    return currentUser
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, isLoading, login, logout }), [
    user, isLoading, login, logout,
  ])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
