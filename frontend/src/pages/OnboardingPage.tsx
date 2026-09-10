import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { updateMe } from '../api/auth'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/apiClient'
import { NIGERIA_STATES } from '../lib/nigeriaStates'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/Banner'
import { SelectField, TextField } from '../components/ui/FormField'

const CURRENT_YEAR = String(new Date().getFullYear())

export function OnboardingPage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: user?.name ?? '',
    occupation_type: '',
    state_residence: '',
    tax_year: CURRENT_YEAR,
  })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await updateMe(form)
      await refreshUser()
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your profile.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-8">
      <div className="w-full max-w-md rounded-2xl bg-surface-container-lowest p-8 shadow-level-1">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-navy">Tell us about you</h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            This helps us tailor your reliefs and filing guidance. You can skip it and fill it in later.
          </p>
        </div>

        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <TextField label="Full Name" value={form.name} onChange={(e) => update('name', e.target.value)} />
          <TextField
            label="Occupation"
            placeholder="e.g. Freelance designer"
            value={form.occupation_type}
            onChange={(e) => update('occupation_type', e.target.value)}
          />
          <SelectField
            label="State of Residence"
            value={form.state_residence}
            onChange={(e) => update('state_residence', e.target.value)}
          >
            <option value="">Select a state...</option>
            {NIGERIA_STATES.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Tax Year"
            maxLength={4}
            value={form.tax_year}
            onChange={(e) => update('tax_year', e.target.value)}
          />
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Save & Continue
          </Button>
        </form>

        <p className="mt-6 text-center text-sm">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="font-semibold text-blue hover:underline"
          >
            Skip for now
          </button>
        </p>
      </div>
    </div>
  )
}
