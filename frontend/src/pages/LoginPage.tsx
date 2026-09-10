import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/apiClient'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/Banner'
import { PasswordField, TextField } from '../components/ui/FormField'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-md rounded-2xl bg-surface-container-lowest p-8 shadow-level-1">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-navy">GigTax</h1>
          <p className="text-sm text-on-surface-variant">Welcome back</p>
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
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <PasswordField
            label="Password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Sign In
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-on-surface-variant">
          New to GigTax?{' '}
          <Link to="/register" className="font-semibold text-blue">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
