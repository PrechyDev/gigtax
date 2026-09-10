import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getMe, login as apiLogin, register as apiRegister, type UserProfile } from '../api/auth'
import { clearToken, getToken, setToken } from '../lib/auth'

interface AuthContextValue {
  user: UserProfile | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (input: Parameters<typeof apiRegister>[0]) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  async function refreshUser() {
    if (!getToken()) {
      setUser(null)
      setIsLoading(false)
      return
    }
    try {
      const profile = await getMe()
      setUser(profile)
    } catch {
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshUser()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function login(email: string, password: string) {
    const { access_token } = await apiLogin({ email, password })
    setToken(access_token)
    await refreshUser()
  }

  async function register(input: Parameters<typeof apiRegister>[0]) {
    const { access_token } = await apiRegister(input)
    setToken(access_token)
    await refreshUser()
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
