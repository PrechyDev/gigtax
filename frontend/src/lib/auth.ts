const TOKEN_KEY = 'gigtax_token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // localStorage can throw in private-browsing/quota-exceeded situations —
    // the user just won't stay logged in across a refresh, not a crash.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // see setToken
  }
}
