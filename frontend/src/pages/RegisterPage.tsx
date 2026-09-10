import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/apiClient'
import { checkPasswordRules } from '../lib/passwordRules'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/Banner'
import { PasswordField, TextField } from '../components/ui/FormField'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [passwordTouched, setPasswordTouched] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const passwordRules = checkPasswordRules(form.password)
  const passwordMeetsAllRules = passwordRules.every((rule) => rule.met)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!passwordMeetsAllRules) {
      setPasswordTouched(true)
      return
    }
    setIsSubmitting(true)
    try {
      await register(form)
      // The rest of the profile (name, occupation, state, tax year) is collected on
      // the next screen — registration itself only ever needed email + password.
      navigate('/onboarding')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-8">
      <div className="w-full max-w-md rounded-2xl bg-surface-container-lowest p-8 shadow-level-1">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-navy">GigTax</h1>
          <p className="text-sm text-on-surface-variant">Create your account</p>
        </div>

        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <TextField
            label="Email"
            type="email"
            required
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
          />
          <PasswordField
            label="Password"
            required
            minLength={8}
            value={form.password}
            onChange={(e) => update('password', e.target.value)}
            onFocus={() => setPasswordTouched(true)}
          />
          {passwordTouched && (
            <ul className="-mt-2 space-y-1 rounded-lg bg-surface-container px-3 py-2 text-xs">
              {passwordRules.map((rule) => (
                <li
                  key={rule.label}
                  className={`flex items-center gap-1.5 ${rule.met ? 'text-emerald' : 'text-on-surface-variant'}`}
                >
                  <span className="material-symbols-outlined text-sm">
                    {rule.met ? 'check_circle' : 'radio_button_unchecked'}
                  </span>
                  {rule.label}
                </li>
              ))}
            </ul>
          )}
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Create Account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-on-surface-variant">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-blue">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
