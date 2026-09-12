import { apiFetch } from '../lib/apiClient'

export interface AdvisoryQueryResponse {
  query_id: string
  session_id: string
  answer: string
  sources: string[]
}

export interface AdvisoryHistoryItem {
  query_id: string
  query_text: string
  response_text: string
  sources: string[]
  timestamp: string
}

export function queryAdvisor(question: string, sessionId?: string) {
  return apiFetch<AdvisoryQueryResponse>('/advisory/query', {
    method: 'POST',
    body: { question, session_id: sessionId },
  })
}

export function getAdvisoryHistory(sessionId: string) {
  return apiFetch<AdvisoryHistoryItem[]>('/advisory/history', { query: { session_id: sessionId } })
}

export interface AdvisorySessionSummary {
  session_id: string
  label: string
  last_active: string
}

export function listAdvisorySessions() {
  return apiFetch<AdvisorySessionSummary[]>('/advisory/sessions')
}

export function deleteAdvisorySession(sessionId: string) {
  return apiFetch<void>(`/advisory/sessions/${sessionId}`, { method: 'DELETE' })
}
