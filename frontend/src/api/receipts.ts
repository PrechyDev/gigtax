import { apiFetch } from '../lib/apiClient'

export interface Receipt {
  receipt_id: string
  transaction_id: string | null
  storage_path: string
  file_type: string | null
  upload_date: string
}

export function listReceipts(transactionId: string) {
  return apiFetch<Receipt[]>(`/transactions/${transactionId}/receipts`)
}

export function uploadReceipt(transactionId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<Receipt>(`/transactions/${transactionId}/receipts`, {
    method: 'POST',
    body: formData,
    isFormData: true,
  })
}
