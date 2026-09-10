export interface PasswordRuleCheck {
  label: string
  met: boolean
}

/** Mirrors backend/schemas/user.py's _validate_password_strength exactly — keep
 * these two in sync if the rule ever changes.
 */
export function checkPasswordRules(password: string): PasswordRuleCheck[] {
  return [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'At least one number', met: /\d/.test(password) },
    { label: 'At least one uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'At least one special character', met: /[^a-zA-Z0-9]/.test(password) },
  ]
}
