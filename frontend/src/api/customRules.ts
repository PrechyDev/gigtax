import { apiFetch } from '../lib/apiClient'

export interface CustomRule {
  rule_id: string
  keyword_pattern: string
  assigned_category: string
  is_active: boolean
}

export interface CustomRuleInput {
  keyword_pattern: string
  assigned_category: string
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
