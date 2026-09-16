import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

type ThemeMode = 'light' | 'dark' | 'auto'

interface ThemeContextType {
  themeMode: ThemeMode
  setThemeMode: (mode: ThemeMode) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('gigtax-theme-mode')
    return (stored as ThemeMode) || 'auto'
  })

  useEffect(() => {
    localStorage.setItem('gigtax-theme-mode', themeMode)

    const applyTheme = () => {
      const root = window.document.documentElement
      root.classList.remove('light', 'dark')

      if (themeMode === 'auto') {
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        root.classList.add(systemPrefersDark ? 'dark' : 'light')
      } else {
        root.classList.add(themeMode)
      }
    }

    applyTheme()

    // Listen to system changes if auto
    if (themeMode === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const listener = () => applyTheme()
      mediaQuery.addEventListener('change', listener)
      return () => mediaQuery.removeEventListener('change', listener)
    }
  }, [themeMode])

  const toggleTheme = () => {
    setThemeMode((prev) => {
      if (prev === 'auto') {
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        return systemPrefersDark ? 'light' : 'dark'
      }
      return prev === 'dark' ? 'light' : 'dark'
    })
  }

  return (
    <ThemeContext.Provider value={{ themeMode, setThemeMode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
