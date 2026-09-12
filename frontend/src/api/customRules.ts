import { apiFetch } from '../lib/apiClient'

export interface CustomRule {
  rule_id: string
  keyword_pattern: string
  assigned_category: string | null
  rule_text: string | null
  is_active: boolean
}

/** Exactly one of assigned_category (quick "map to a category" mode) or rule_text
 * (freeform natural-language instruction, e.g. "these are personal, exclude them
 * from business income/expense") must be set — enforced by the backend schema.
 */
export interface CustomRuleInput {
  keyword_pattern: string
  assigned_category?: string
  rule_text?: string
}

export function listCustomRules() {
  return apiFetch<CustomRule[]>('/custom-rules')
}

export function createCustomRule(input: CustomRuleInput) {
  return apiFetch<CustomRule>('/custom-rules', { method: 'POST', body: input })
}

export function deleteCustomRule(ruleId: string) {
  return apiFetch<void>(`/custom-rules/${ruleId}`, { method: 'DELETE' })
}
