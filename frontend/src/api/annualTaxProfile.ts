import { apiFetch } from '../lib/apiClient'

/** Rent paid and home-office claim, scoped to a single tax year — these genuinely
 * change year to year, unlike TIN or state of residence, so they live per-year
 * rather than as a single static profile field. See Reports page.
 */
export interface AnnualTaxProfile {
  tax_year: string
  annual_rent_paid: number | null
  has_home_office: boolean
  home_office_percentage: number
}

export interface AnnualTaxProfileInput {
  annual_rent_paid: number | null
  has_home_office: boolean
  home_office_percentage: number
}

export function getAnnualTaxProfile(taxYear: string) {
  return apiFetch<AnnualTaxProfile>(`/tax-computations/${taxYear}/annual-profile`)
}

export function updateAnnualTaxProfile(taxYear: string, input: AnnualTaxProfileInput) {
  return apiFetch<AnnualTaxProfile>(`/tax-computations/${taxYear}/annual-profile`, {
    method: 'PUT',
    body: input,
  })
}
