import { apiFetch } from '../lib/apiClient'

export interface Transaction {
  transaction_id: string
  statement_id: string | null
  type: 'income' | 'expense'
  date: string
  description: string
  amount: number
  currency: string
  ai_category_id: string | null
  user_category_id: string | null
  confidence_score: number | null
  review_status: 'PENDING' | 'APPROVED' | 'REJECTED'
  tax_treatment: string | null
  source: string
  discarded_at: string | null
}

export interface ManualTransactionInput {
  transaction_type: 'income' | 'expense'
  date: string
  description: string
  amount: number
  currency?: string
  category_slug?: string
  income_source?: string
  merchant_name?: string
}

export interface TransactionReviewInput {
  review_status?: 'APPROVED' | 'REJECTED' | 'PENDING'
  category_slug?: string
  description?: string
}

export interface TransactionFilters {
  review_status?: string
  tax_year?: string
  transaction_type?: string
  category_slug?: string
  exclude_uncategorized?: boolean
  limit?: number
  offset?: number
  [key: string]: string | number | boolean | undefined
}

export function listTransactions(filters: TransactionFilters = {}) {
  return apiFetch<Transaction[]>('/transactions', { query: filters })
}

export function createManualTransaction(input: ManualTransactionInput) {
  return apiFetch<Transaction>('/transactions', { method: 'POST', body: input })
}

export function reviewTransaction(transactionId: string, input: TransactionReviewInput) {
  return apiFetch<Transaction>(`/transactions/${transactionId}`, { method: 'PATCH', body: input })
}

export function deleteTransaction(transactionId: string) {
  return apiFetch<void>(`/transactions/${transactionId}`, { method: 'DELETE' })
}

/** One request instead of N — see backend/api/routes/transactions.py's
 * bulk_review_transactions. Setting REJECTED here is a discard (recoverable for 30
 * days from the Discarded tab), not a permanent delete.
 */
export function bulkReviewTransactions(transactionIds: string[], reviewStatus: 'APPROVED' | 'REJECTED' | 'PENDING') {
  return apiFetch<Transaction[]>('/transactions/bulk-review', {
    method: 'PATCH',
    body: { transaction_ids: transactionIds, review_status: reviewStatus },
  })
}

/** Permanent, immediate delete for multiple transactions at once — only reachable
 * from the Discarded tab's "delete now" action, skipping the 30-day recovery window.
 */
export function bulkDeleteTransactions(transactionIds: string[]) {
  return apiFetch<void>('/transactions/bulk', {
    method: 'DELETE',
    body: { transaction_ids: transactionIds },
  })
}
