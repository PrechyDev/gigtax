import { apiFetch } from '../lib/apiClient'

export interface BandBreakdownItem {
  rate: number
  amount_in_band: number
  tax: number
}

export interface TaxComputation {
  tax_year: string
  total_income: number
  total_deductions: number
  total_reliefs: number
  total_capital_allowances: number
  taxable_income: number
  estimated_tax_owed: number
  minimum_wage_exempt: boolean
  band_breakdown: BandBreakdownItem[]
  last_updated: string | null
}

export function getTaxComputation(taxYear: string) {
  return apiFetch<TaxComputation>(`/tax-computations/${taxYear}`)
}

export function computeTax(taxYear: string) {
  return apiFetch<TaxComputation>(`/tax-computations/${taxYear}/compute`, { method: 'POST' })
}

export async function downloadReport(taxYear: string): Promise<Blob> {
  return apiFetch<Blob>(`/tax-computations/${taxYear}/report`)
}

export interface DashboardData {
  tax_year: string
  total_income: number
  total_deductions: number
  total_reliefs: number
  total_capital_allowances: number
  estimated_tax_owed: number
  pending_review_count: number
  locked_statements_count: number
  missing_receipts_count: number
  google_drive_connected: boolean
  filing_guidance: string
  outstanding_actions: string[]
}

export function getDashboard(taxYear: string) {
  return apiFetch<DashboardData>('/dashboard', { query: { tax_year: taxYear } })
}
