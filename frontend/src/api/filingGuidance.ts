import { apiFetch } from '../lib/apiClient'

export interface FilingGuidance {
  state: string | null
  portal_name: string | null
  portal_url: string | null
  note: string
}

export function getFilingGuidance(state?: string) {
  return apiFetch<FilingGuidance>('/filing-guidance', { query: state ? { state } : {} })
}
