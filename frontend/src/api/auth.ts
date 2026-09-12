import { apiFetch } from '../lib/apiClient'

export interface UserProfile {
  user_id: string
  name: string
  email: string
  occupation_type: string | null
  state_residence: string | null
  tax_year: string | null
  tin: string | null
  google_drive_connected: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterInput {
  email: string
  password: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface ProfileUpdateInput {
  name?: string
  occupation_type?: string
  state_residence?: string
  tax_year?: string
  tin?: string
}

export function register(input: RegisterInput) {
  return apiFetch<TokenResponse>('/auth/register', { method: 'POST', body: input })
}

export function login(input: LoginInput) {
  return apiFetch<TokenResponse>('/auth/login', { method: 'POST', body: input })
}

export function getMe() {
  return apiFetch<UserProfile>('/auth/me')
}

export function updateMe(input: ProfileUpdateInput) {
  return apiFetch<UserProfile>('/auth/me', { method: 'PATCH', body: input })
}
