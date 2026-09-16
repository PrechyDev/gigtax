import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { updateMe } from '../api/auth'
import { getGoogleDriveConnectUrl } from '../api/drive'
import { updateAnnualTaxProfile } from '../api/annualTaxProfile'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../lib/apiClient'
import { NIGERIA_STATES } from '../lib/nigeriaStates'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { SelectField, TextField } from '../components/ui/FormField'

const CURRENT_YEAR = String(new Date().getFullYear())
const RESUME_FLAG = 'gigtax-onboarding-resume'

const OCCUPATION_OPTIONS = [
  'Freelance designer or developer',
  'Consultant',
  'Content creator',
  'Ride-hailing or delivery driver',
  'Tutor or teacher',
  'Photographer or videographer',
  'Trader or reseller',
  'Other',
]

const TOTAL_STEPS = 3

export function OnboardingPage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [step, setStep] = useState(1)
  const [basics, setBasics] = useState({
    name: user?.name ?? '',
    occupation_type: '',
    occupation_other: '',
    state_residence: '',
  })
  const [homeOffice, setHomeOffice] = useState({ has_home_office: false, home_office_percentage: 0 })
  const [driveConnected, setDriveConnected] = useState(false)
  const [driveError, setDriveError] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const resumeStep = searchParams.get('resumeStep')
    if (resumeStep === '3') {
      setStep(3)
      if (searchParams.get('drive') === 'connected') setDriveConnected(true)
      if (searchParams.get('drive') === 'error') setDriveError(true)
    }
  }, [searchParams])

  function updateBasics<K extends keyof typeof basics>(key: K, value: (typeof basics)[K]) {
    setBasics((prev) => ({ ...prev, [key]: value }))
  }

  const canContinue =
    step !== 1 ||
    (basics.name.trim() !== '' &&
      basics.occupation_type !== '' &&
      (basics.occupation_type !== 'Other' || basics.occupation_other.trim() !== '') &&
      basics.state_residence !== '')

  async function saveProgress() {
    const occupation = basics.occupation_type === 'Other' ? basics.occupation_other : basics.occupation_type
    await updateMe({
      name: basics.name,
      occupation_type: occupation,
      state_residence: basics.state_residence,
      tax_year: CURRENT_YEAR,
    })
    await updateAnnualTaxProfile(CURRENT_YEAR, {
      annual_rent_paid: null,
      has_home_office: homeOffice.has_home_office,
      home_office_percentage: homeOffice.home_office_percentage,
    })
  }

  async function handleFinish() {
    setError(null)
    setIsSubmitting(true)
    try {
      await saveProgress()
      await refreshUser()
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your profile.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleConnectDrive() {
    setError(null)
    setIsSubmitting(true)
    try {
      await saveProgress()
      localStorage.setItem(RESUME_FLAG, '1')
      window.location.href = getGoogleDriveConnectUrl()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your profile.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-8">
      <div className="w-full max-w-[460px] rounded-2xl bg-surface-container-lowest p-8 shadow-level-1">
        <div className="mb-1 h-1.5 w-full rounded-full bg-surface-container">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${(step / TOTAL_STEPS) * 100}%` }}
          />
        </div>
        <p className="mb-6 text-xs text-on-surface-variant">
          Step {step} of {TOTAL_STEPS}
        </p>

        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} />
          </div>
        )}

        {step === 1 && (
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-xl font-bold text-navy">Tell us about you</h1>
              <p className="mt-1 text-sm text-on-surface-variant">
                This helps us tailor your reliefs and filing guidance.
              </p>
            </div>
            <TextField
              label="Full name"
              value={basics.name}
              onChange={(e) => updateBasics('name', e.target.value)}
            />
            <SelectField
              label="Occupation type"
              value={basics.occupation_type}
              onChange={(e) => updateBasics('occupation_type', e.target.value)}
            >
              <option value="">Select an occupation...</option>
              {OCCUPATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </SelectField>
            {basics.occupation_type === 'Other' && (
              <TextField
                label="Describe your occupation"
                value={basics.occupation_other}
                onChange={(e) => updateBasics('occupation_other', e.target.value)}
              />
            )}
            <SelectField
              label="State of residence"
              value={basics.state_residence}
              onChange={(e) => updateBasics('state_residence', e.target.value)}
            >
              <option value="">Select a state...</option>
              {NIGERIA_STATES.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </SelectField>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-xl font-bold text-navy">Home office</h1>
              <p className="mt-1 text-sm text-on-surface-variant">
                If you work from home, we can deduct part of your rent and utility bills as a business
                expense.
              </p>
            </div>
            <div className="flex w-fit overflow-hidden rounded-md border border-outline-variant text-sm">
              <button
                type="button"
                onClick={() => setHomeOffice((h) => ({ ...h, has_home_office: false }))}
                className={`px-4 py-1.5 ${
                  !homeOffice.has_home_office ? 'bg-accent text-bg' : 'bg-surface-container-lowest'
                }`}
              >
                No
              </button>
              <button
                type="button"
                onClick={() => setHomeOffice((h) => ({ ...h, has_home_office: true }))}
                className={`border-l border-outline-variant px-4 py-1.5 ${
                  homeOffice.has_home_office ? 'bg-accent text-bg' : 'bg-surface-container-lowest'
                }`}
              >
                Yes
              </button>
            </div>
            {homeOffice.has_home_office && (
              <div className="flex flex-col gap-1">
                <label className="text-sm">
                  Home office share ({homeOffice.home_office_percentage}%)
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={homeOffice.home_office_percentage}
                  onChange={(e) =>
                    setHomeOffice((h) => ({ ...h, home_office_percentage: Number(e.target.value) }))
                  }
                  className="w-full"
                />
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-xl font-bold text-navy">Connect Google Drive</h1>
              <p className="mt-1 text-sm text-on-surface-variant">
                GigTax works even without this step. If you connect your Drive, statements and reports are
                stored directly in your own Google account, in a dedicated GigTax folder, never on our
                servers. You can disconnect at any time from Settings.
              </p>
            </div>

            {driveConnected && (
              <SuccessBanner message="Google Drive connected successfully." onDismiss={() => setDriveConnected(false)} />
            )}
            {driveError && (
              <ErrorBanner
                message="Could not connect to Google Drive. You can try again from Settings later."
                onDismiss={() => setDriveError(false)}
              />
            )}

            <div className="flex items-center gap-3 rounded-lg border border-divider bg-surface p-4">
              <span className="material-symbols-outlined shrink-0 text-xl text-accent">cloud</span>
              <div className="flex-1">
                <p className="m-0 text-sm font-semibold">Google Drive</p>
                <p className="m-0 text-xs text-on-surface-variant">
                  {driveConnected ? 'Connected' : 'Not connected'}
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={driveConnected || isSubmitting}
                onClick={handleConnectDrive}
              >
                {driveConnected ? 'Connected' : 'Connect Google Drive'}
              </Button>
            </div>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between">
          <Button
            type="button"
            variant="secondary"
            disabled={step === 1}
            onClick={() => setStep((s) => s - 1)}
          >
            Back
          </Button>
          {step < TOTAL_STEPS ? (
            <Button type="button" disabled={!canContinue} onClick={() => setStep((s) => s + 1)}>
              Continue
            </Button>
          ) : (
            <Button type="button" isLoading={isSubmitting} onClick={handleFinish}>
              Finish setup
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
