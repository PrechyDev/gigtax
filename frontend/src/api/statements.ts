import { apiFetch } from '../lib/apiClient'

export interface StatementFileResult {
  statement_id: string
  file_name: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'LOCKED'
  transactions_created: number
  requires_password: boolean
  error: string | null
}

export interface StatementListItem {
  statement_id: string
  file_name: string
  source_type: string | null
  parsing_status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'LOCKED'
  upload_date: string
  transactions_created: number
  error_message: string | null
}

export function uploadStatements(files: File[]) {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  return apiFetch<{ results: StatementFileResult[] }>('/statements', {
    method: 'POST',
    body: formData,
    isFormData: true,
  })
}

export function retryLockedStatement(statementId: string, file: File, password: string) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('password', password)
  return apiFetch<StatementFileResult>(`/statements/${statementId}/retry`, {
    method: 'POST',
    body: formData,
    isFormData: true,
  })
}

export function listStatements() {
  return apiFetch<StatementListItem[]>('/statements')
}
