import { clearToken, getToken } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string

/** Thrown for any non-2xx response. `message` is always the backend's `detail`
 * field — already a user-safe, friendly string (see backend's global exception
 * handler and per-route error wrapping) — never a raw status code or stack trace.
 */
export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.'

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    // FastAPI validation errors (422) come back as detail: [{msg, loc, ...}, ...]
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      return body.detail.map((d: { msg: string }) => d.msg).join(' ')
    }
  } catch {
    // response wasn't JSON at all — fall through to the generic message
  }
  return GENERIC_ERROR_MESSAGE
}

interface RequestOptions {
  method?: string
  body?: unknown
  isFormData?: boolean
  query?: Record<string, string | number | boolean | undefined>
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(path, API_BASE_URL)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, isFormData = false, query } = options
  const token = getToken()

  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!isFormData && body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    // Network failure (server down, no connection) — fetch itself throws, there's
    // no response/detail to read here at all.
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0)
  }

  if (response.status === 401) {
    clearToken()
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new ApiError('Your session has expired. Please log in again.', 401)
  }

  if (!response.ok) {
    throw new ApiError(await parseErrorDetail(response), response.status)
  }

  if (response.status === 204) return undefined as T

  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return (await response.json()) as T
  }
  return (await response.blob()) as unknown as T
}
