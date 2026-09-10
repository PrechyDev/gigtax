import { getToken } from '../lib/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

/** /auth/google/connect is a redirect, not a JSON API — the browser navigates there
 * directly (can't be a fetch call, since we need the actual OAuth consent screen).
 * The backend expects a Bearer token, so it's passed as a query param here since a
 * full-page navigation can't set an Authorization header.
 *
 * NOTE: this requires the backend's /auth/google/connect to also accept the token
 * via a query param, not just the Authorization header — see the corresponding
 * backend change.
 */
export function getGoogleDriveConnectUrl(): string {
  const token = getToken()
  return `${API_BASE_URL}/auth/google/connect?token=${encodeURIComponent(token ?? '')}`
}
