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
}

export interface TransactionFilters {
  review_status?: string
  tax_year?: string
  transaction_type?: string
  [key: string]: string | undefined
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
