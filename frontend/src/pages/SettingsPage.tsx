import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { updateMe } from '../api/auth'
import { getGoogleDriveConnectUrl } from '../api/drive'
import { listCategories, type Category } from '../api/categories'
import { createCustomRule, deleteCustomRule, listCustomRules } from '../api/customRules'
import { classificationLabel } from '../lib/categoryLabels'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { PageSpinner, Spinner } from '../components/ui/Spinner'
import { SelectField, TextField } from '../components/ui/FormField'
import { NIGERIA_STATES } from '../lib/nigeriaStates'
import { ApiError } from '../lib/apiClient'

export function SettingsPage() {
  return (
    <AppShell title="Settings">
      <div className="mx-auto flex max-w-[620px] flex-col gap-6">
        <div>
          <h3 className="mb-1 text-xl font-semibold text-navy">Settings</h3>
        </div>

        <ProfileSection />
        <IntegrationsSection />
        <RulesSection />
        <AppearanceSection />

        <LogoutSection />
      </div>
    </AppShell>
  )
}

function ProfileSection() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    name: user?.name ?? '',
    occupation_type: user?.occupation_type ?? '',
    state_residence: user?.state_residence ?? '',
    tax_year: user?.tax_year ?? '',
    tin: user?.tin ?? '',
  })
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: updateMe,
    onSuccess: async () => {
      await refreshUser()
      setSuccess(true)
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not save your profile.'),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSuccess(false)
    mutation.mutate(form)
  }

  return (
    <div className="flex flex-col gap-3">
      <h6 className="m-0 text-sm font-semibold text-on-surface-variant">Profile</h6>
      
      {error && <ErrorBanner message={error} />}
      {success && <SuccessBanner message="Profile updated successfully." onDismiss={() => setSuccess(false)} />}
      
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <TextField label="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <SelectField
          label="State of residence"
          value={form.state_residence}
          onChange={(e) => setForm({ ...form, state_residence: e.target.value })}
        >
          <option value="">Select a state...</option>
          {NIGERIA_STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </SelectField>
        <TextField
          label="Primary occupation"
          value={form.occupation_type}
          onChange={(e) => setForm({ ...form, occupation_type: e.target.value })}
        />
        <TextField
          label="Tax Identification Number (TIN)"
          value={form.tin}
          onChange={(e) => setForm({ ...form, tin: e.target.value })}
        />
        <TextField
          label="Tax year"
          value={form.tax_year}
          maxLength={4}
          onChange={(e) => setForm({ ...form, tax_year: e.target.value })}
        />

        <Button type="submit" isLoading={mutation.isPending} className="self-start">
          Save Changes
        </Button>
      </form>
    </div>
  )
}

const ONBOARDING_RESUME_FLAG = 'gigtax-onboarding-resume'

function IntegrationsSection() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [driveSuccess, setDriveSuccess] = useState(false)
  const [driveError, setDriveError] = useState(false)

  useEffect(() => {
    const driveResult = searchParams.get('drive')
    if (!driveResult) return

    if (localStorage.getItem(ONBOARDING_RESUME_FLAG)) {
      localStorage.removeItem(ONBOARDING_RESUME_FLAG)
      navigate(`/onboarding?resumeStep=3&drive=${driveResult}`, { replace: true })
      return
    }

    if (driveResult === 'connected') {
      setDriveSuccess(true)
    } else if (driveResult === 'error') {
      setDriveError(true)
    }
  }, [searchParams, navigate])

  return (
    <div className="flex flex-col gap-2">
      <h6 className="m-0 text-sm font-semibold text-on-surface-variant">Storage</h6>
      
      {driveSuccess && (
        <div className="mb-2">
          <SuccessBanner message="Google Drive connected successfully." onDismiss={() => setDriveSuccess(false)} />
        </div>
      )}
      {driveError && (
        <div className="mb-2">
          <ErrorBanner
            message="Could not connect to Google Drive. Please try again."
            onDismiss={() => setDriveError(false)}
          />
        </div>
      )}

      <div className="flex flex-row items-center gap-3 rounded-lg border border-divider bg-surface p-4 shadow-sm">
        <span className="material-symbols-outlined shrink-0 text-xl text-accent">cloud</span>
        <div className="flex-1">
          <p className="m-0 text-sm font-semibold">Google Drive</p>
          <p className="m-0 flex items-center gap-1.5 text-xs text-on-surface-variant">
            <span
              className={`h-2 w-2 rounded-full ${user?.google_drive_connected ? 'bg-emerald' : 'bg-outline'}`}
            />
            {user?.google_drive_connected ? 'Connected' : 'Not Connected'}
          </p>
        </div>
        {!user?.google_drive_connected ? (
          <a href={getGoogleDriveConnectUrl()}>
            <Button variant="secondary">Connect Drive</Button>
          </a>
        ) : (
          <Button variant="secondary" disabled>Connected</Button>
        )}
      </div>
    </div>
  )
}

type RuleMode = 'category' | 'freeform'

function RulesSection() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<RuleMode>('category')
  const [pattern, setPattern] = useState('')
  const [category, setCategory] = useState('')
  const [ruleText, setRuleText] = useState('')
  const [error, setError] = useState<string | null>(null)

  const rulesQuery = useQuery({ queryKey: ['custom-rules'], queryFn: listCustomRules })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategories })

  const groupedCategories = (categoriesQuery.data ?? []).reduce<Record<string, Category[]>>((groups, c) => {
    // Only grouping expenses for the UI as per the redesign spec or general groupings
    const label = classificationLabel(c.classification)
    groups[label] = [...(groups[label] ?? []), c]
    return groups
  }, {})

  const createMutation = useMutation({
    mutationFn: createCustomRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-rules'] })
      setPattern('')
      setCategory('')
      setRuleText('')
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not create this rule.'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCustomRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['custom-rules'] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not delete this rule.'),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!pattern.trim()) return
    if (mode === 'category') {
      if (!category.trim()) return
      createMutation.mutate({ keyword_pattern: pattern, assigned_category: category })
    } else {
      if (!ruleText.trim()) return
      createMutation.mutate({ keyword_pattern: pattern, rule_text: ruleText })
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <h6 className="m-0 text-sm font-semibold text-on-surface-variant">Custom rules</h6>
      <p className="m-0 text-xs text-on-surface-variant">
        When a description contains this keyword, apply this category automatically next time it shows up.
      </p>

      {error && (
        <div className="mb-2">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      <div className="flex flex-col gap-0 rounded-lg border border-divider bg-surface shadow-sm">
        {rulesQuery.isLoading && <div className="p-4"><PageSpinner /></div>}
        
        {rulesQuery.data && rulesQuery.data.length > 0 && (
          <div>
            {rulesQuery.data.map((rule) => (
              <div
                key={rule.rule_id}
                className="flex items-center gap-2 border-b border-divider p-3"
              >
                <span className="text-sm font-semibold">"{rule.keyword_pattern}"</span>
                <span className="material-symbols-outlined shrink-0 text-sm text-on-surface-variant">arrow_forward</span>
                <span className="flex-1 text-sm">
                  {rule.assigned_category ? rule.assigned_category : rule.rule_text}
                </span>
                <button
                  onClick={() => deleteMutation.mutate(rule.rule_id)}
                  disabled={deleteMutation.isPending}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-on-surface-variant hover:bg-surface-container-high hover:text-error"
                  title="Remove rule"
                  aria-label="Remove rule"
                >
                  {deleteMutation.isPending ? <Spinner size={14} /> : <span className="material-symbols-outlined text-sm">close</span>}
                </button>
              </div>
            ))}
          </div>
        )}

        {rulesQuery.data && rulesQuery.data.length === 0 && (
          <p className="m-0 p-3 text-sm text-on-surface-variant">No custom rules yet.</p>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-2 p-3">
          <div className="flex w-fit overflow-hidden rounded-md text-xs">
            <label className="relative flex items-center justify-center bg-surface-container-low">
              <input
                type="radio"
                name="rulemode"
                className="peer sr-only"
                checked={mode === 'category'}
                onChange={() => setMode('category')}
              />
              <span className="cursor-pointer px-2.5 py-1.5 peer-checked:bg-accent peer-checked:text-bg">Map to a category</span>
            </label>
            <label className="relative flex items-center justify-center bg-surface-container-low">
              <input 
                type="radio" 
                name="rulemode" 
                className="peer sr-only"
                checked={mode === 'freeform'} 
                onChange={() => setMode('freeform')} 
              />
              <span className="cursor-pointer px-2.5 py-1.5 peer-checked:bg-accent peer-checked:text-bg">Describe what to do</span>
            </label>
          </div>
          
          <input
            className="h-10 w-full rounded-md border border-outline-variant bg-transparent px-3 text-sm focus:border-accent focus:outline-none"
            required
            placeholder="Keyword, e.g. UBER *TRIP"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
          />
          
          {mode === 'category' ? (
            <div className="flex flex-wrap gap-2">
              <select
                className="h-10 flex-1 min-w-[160px] rounded-md border border-outline-variant bg-transparent px-3 text-sm focus:border-accent focus:outline-none"
                required
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="" disabled>Category</option>
                {Object.entries(groupedCategories).map(([label, cats]) => (
                  <optgroup key={label} label={label}>
                    {(cats ?? []).map((c) => (
                      <option key={c.developer_slug} value={c.developer_slug}>
                        {c.category_name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <Button type="submit" variant="secondary" isLoading={createMutation.isPending}>Add rule</Button>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <input
                className="h-10 flex-1 min-w-[180px] rounded-md border border-outline-variant bg-transparent px-3 text-sm focus:border-accent focus:outline-none"
                required
                placeholder="Natural rule, e.g. treat as a business expense"
                value={ruleText}
                onChange={(e) => setRuleText(e.target.value)}
              />
              <Button type="submit" variant="secondary" isLoading={createMutation.isPending}>Add rule</Button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}

function AppearanceSection() {
  const { themeMode, setThemeMode } = useTheme()

  return (
    <div className="flex flex-col gap-2">
      <h6 className="m-0 text-sm font-semibold text-on-surface-variant">Appearance</h6>
      <div className="flex w-fit overflow-hidden rounded-md border border-outline-variant bg-surface text-sm">
        <label className="relative flex items-center justify-center">
          <input
            type="radio"
            name="theme"
            className="peer sr-only"
            checked={themeMode === 'light'}
            onChange={() => setThemeMode('light')}
          />
          <span className="cursor-pointer px-4 py-1.5 peer-checked:bg-accent peer-checked:text-bg">Light</span>
        </label>
        <label className="relative flex items-center justify-center border-l border-outline-variant">
          <input
            type="radio"
            name="theme"
            className="peer sr-only"
            checked={themeMode === 'dark'}
            onChange={() => setThemeMode('dark')}
          />
          <span className="cursor-pointer px-4 py-1.5 peer-checked:bg-accent peer-checked:text-bg">Dark</span>
        </label>
        <label className="relative flex items-center justify-center border-l border-outline-variant">
          <input 
            type="radio" 
            name="theme" 
            className="peer sr-only"
            checked={themeMode === 'auto'} 
            onChange={() => setThemeMode('auto')} 
          />
          <span className="cursor-pointer px-4 py-1.5 peer-checked:bg-accent peer-checked:text-bg">Auto</span>
        </label>
      </div>
    </div>
  )
}

function LogoutSection() {
  const { logout } = useAuth()
  return (
    <Button variant="secondary" className="mt-2 self-start" onClick={logout}>
      <span className="material-symbols-outlined -ml-1 mr-1 text-[18px]">logout</span>
      Log out
    </Button>
  )
}
