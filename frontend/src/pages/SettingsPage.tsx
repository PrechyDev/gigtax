import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { updateMe } from '../api/auth'
import { getGoogleDriveConnectUrl } from '../api/drive'
import { listCategories, type Category } from '../api/categories'
import { createCustomRule, deleteCustomRule, listCustomRules } from '../api/customRules'
import { classificationLabel } from '../lib/categoryLabels'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { EmptyState } from '../components/ui/EmptyState'
import { PageSpinner, Spinner } from '../components/ui/Spinner'
import { SelectField, TextField } from '../components/ui/FormField'
import { NIGERIA_STATES } from '../lib/nigeriaStates'
import { ApiError } from '../lib/apiClient'

type Tab = 'profile' | 'integrations' | 'rules'

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>('profile')
  const [searchParams] = useSearchParams()
  const [driveSuccess, setDriveSuccess] = useState(false)
  const [driveError, setDriveError] = useState(false)

  useEffect(() => {
    if (searchParams.get('drive') === 'connected') {
      setDriveSuccess(true)
      setTab('integrations')
    } else if (searchParams.get('drive') === 'error') {
      setDriveError(true)
      setTab('integrations')
    }
  }, [searchParams])

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: 'profile', label: 'Profile Details', icon: 'person' },
    { id: 'integrations', label: 'Integrations', icon: 'cloud' },
    { id: 'rules', label: 'AI Custom Rules', icon: 'rule' },
  ]

  return (
    <AppShell title="Settings & Integrations">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
        <nav className="md:col-span-3">
          <ul className="space-y-1">
            {TABS.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => setTab(t.id)}
                  className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium ${
                    tab === t.id ? 'bg-blue/10 text-blue-dark' : 'text-on-surface-variant hover:bg-surface-container-low'
                  }`}
                >
                  <span className="material-symbols-outlined text-lg">{t.icon}</span>
                  {t.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="md:col-span-9">
          {tab === 'profile' && <ProfileTab />}
          {tab === 'integrations' && (
            <IntegrationsTab
              showSuccess={driveSuccess}
              onDismissSuccess={() => setDriveSuccess(false)}
              showError={driveError}
              onDismissError={() => setDriveError(false)}
            />
          )}
          {tab === 'rules' && <RulesTab />}
        </div>
      </div>
    </AppShell>
  )
}

function ProfileTab() {
  const { user, refreshUser } = useAuth()
  const [form, setForm] = useState({
    name: user?.name ?? '',
    occupation_type: user?.occupation_type ?? '',
    state_residence: user?.state_residence ?? '',
    tax_year: user?.tax_year ?? '',
    tin: user?.tin ?? '',
    has_home_office: user?.has_home_office ?? false,
    home_office_percentage: user?.home_office_percentage ?? 0,
    annual_rent_paid: user?.annual_rent_paid ?? '',
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
    mutation.mutate({
      ...form,
      annual_rent_paid: form.annual_rent_paid === '' ? undefined : Number(form.annual_rent_paid),
    })
  }

  return (
    <div className="rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
      <h3 className="mb-4 font-semibold text-navy">Legal & Tax Information</h3>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      {success && (
        <div className="mb-4">
          <SuccessBanner message="Profile updated successfully." onDismiss={() => setSuccess(false)} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField label="Full Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <TextField
          label="Tax Identification Number (TIN)"
          value={form.tin}
          onChange={(e) => setForm({ ...form, tin: e.target.value })}
        />
        <SelectField
          label="State of Residence"
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
          label="Occupation"
          value={form.occupation_type}
          onChange={(e) => setForm({ ...form, occupation_type: e.target.value })}
        />
        <TextField
          label="Tax Year"
          value={form.tax_year}
          maxLength={4}
          onChange={(e) => setForm({ ...form, tax_year: e.target.value })}
        />
        <TextField
          label="Annual Rent Paid (NGN)"
          type="number"
          min={0}
          step="0.01"
          value={form.annual_rent_paid}
          onChange={(e) => setForm({ ...form, annual_rent_paid: e.target.value === '' ? '' : Number(e.target.value) })}
        />
        <p className="-mt-3 text-xs text-on-surface-variant">
          Enter what you pay in rent per year. We'll automatically work out your rent relief — and, if you
          claim a home office below, split off that portion as a business expense instead.
        </p>

        <div className="rounded-lg border border-outline-variant p-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.has_home_office}
              onChange={(e) => setForm({ ...form, has_home_office: e.target.checked })}
            />
            <span className="text-sm font-semibold">Home Office Deduction</span>
          </label>
          {form.has_home_office && (
            <div className="mt-3">
              <label className="mb-1 block text-sm text-on-surface-variant">
                {form.home_office_percentage}% of your rent counts as a home-office business expense
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={form.home_office_percentage}
                onChange={(e) => setForm({ ...form, home_office_percentage: Number(e.target.value) })}
                className="w-full"
              />
              <p className="mt-1 text-xs text-emerald-dark">
                The rest of your rent still counts toward your rent relief (20%, capped at ₦500,000).
              </p>
            </div>
          )}
        </div>

        <Button type="submit" isLoading={mutation.isPending}>
          Save Changes
        </Button>
      </form>
    </div>
  )
}

function IntegrationsTab({
  showSuccess,
  onDismissSuccess,
  showError,
  onDismissError,
}: {
  showSuccess: boolean
  onDismissSuccess: () => void
  showError: boolean
  onDismissError: () => void
}) {
  const { user } = useAuth()

  return (
    <div className="rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
      <h3 className="mb-1 font-semibold text-navy">Bring Your Own Storage (BYOS)</h3>
      <p className="mb-4 text-sm text-on-surface-variant">
        Receipts and documents are stored in your own Google Drive, not on our servers — you stay in control.
      </p>
      {showSuccess && (
        <div className="mb-4">
          <SuccessBanner message="Google Drive connected successfully." onDismiss={onDismissSuccess} />
        </div>
      )}
      {showError && (
        <div className="mb-4">
          <ErrorBanner
            message="Could not connect to Google Drive. Please try again."
            onDismiss={onDismissError}
          />
        </div>
      )}
      <div className="flex items-center justify-between rounded-lg border border-outline-variant p-4">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-2xl text-blue">cloud</span>
          <div>
            <p className="font-medium">Google Drive</p>
            <p className="flex items-center gap-1.5 text-xs text-on-surface-variant">
              <span
                className={`h-2 w-2 rounded-full ${user?.google_drive_connected ? 'bg-emerald' : 'bg-outline'}`}
              />
              {user?.google_drive_connected ? 'Connected' : 'Not Connected'}
            </p>
          </div>
        </div>
        {!user?.google_drive_connected && (
          <a href={getGoogleDriveConnectUrl()}>
            <Button>Connect Drive</Button>
          </a>
        )}
      </div>
    </div>
  )
}

type RuleMode = 'category' | 'freeform'

function RulesTab() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<RuleMode>('category')
  const [pattern, setPattern] = useState('')
  const [category, setCategory] = useState('')
  const [ruleText, setRuleText] = useState('')
  const [error, setError] = useState<string | null>(null)

  const rulesQuery = useQuery({ queryKey: ['custom-rules'], queryFn: listCustomRules })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategories })

  const groupedCategories = (categoriesQuery.data ?? []).reduce<Record<string, Category[]>>((groups, c) => {
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
    <div className="rounded-lg border-l-4 border-blue bg-surface-container-lowest p-6 shadow-level-1">
      <h3 className="mb-1 font-semibold text-navy">AI Custom Rules</h3>
      <p className="mb-4 text-sm text-on-surface-variant">
        Teach the AI to automatically categorize recurring transactions — map a keyword straight to a category, or
        describe in your own words what should happen (e.g. "these are personal transfers between my own
        accounts, not business income or expenses").
      </p>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {rulesQuery.isLoading && <PageSpinner />}
      {rulesQuery.data && rulesQuery.data.length === 0 && (
        <EmptyState icon="rule" message="No custom rules yet — add one below." />
      )}
      {rulesQuery.data && rulesQuery.data.length > 0 && (
        <ul className="mb-4 space-y-2">
          {rulesQuery.data.map((rule) => (
            <li
              key={rule.rule_id}
              className="flex items-start justify-between gap-3 rounded-md bg-surface-container-low px-3 py-2 text-sm"
            >
              <span className="italic">
                "{rule.keyword_pattern}"{' '}
                {rule.assigned_category ? (
                  <>→ {rule.assigned_category}</>
                ) : (
                  <span className="not-italic text-on-surface-variant">— {rule.rule_text}</span>
                )}
              </span>
              <button
                onClick={() => deleteMutation.mutate(rule.rule_id)}
                disabled={deleteMutation.isPending}
                className="shrink-0 text-on-surface-variant hover:text-error"
                aria-label="Delete rule"
              >
                {deleteMutation.isPending ? <Spinner size={14} /> : <span className="material-symbols-outlined text-lg">close</span>}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mb-3 flex gap-1 rounded-lg bg-surface-container-low p-1 text-sm">
        <button
          type="button"
          onClick={() => setMode('category')}
          className={`flex-1 rounded-md px-3 py-1.5 font-medium transition-colors ${
            mode === 'category' ? 'bg-surface-container-lowest text-blue-dark shadow-level-1' : 'text-on-surface-variant'
          }`}
        >
          Map to a category
        </button>
        <button
          type="button"
          onClick={() => setMode('freeform')}
          className={`flex-1 rounded-md px-3 py-1.5 font-medium transition-colors ${
            mode === 'freeform' ? 'bg-surface-container-lowest text-blue-dark shadow-level-1' : 'text-on-surface-variant'
          }`}
        >
          Describe what to do
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-2">
        <input
          value={pattern}
          onChange={(e) => setPattern(e.target.value)}
          placeholder="Keyword (e.g. 'MTN' or 'internal transfer')"
          className="h-10 w-full rounded-md border border-outline-variant px-3 text-sm"
        />
        {mode === 'category' ? (
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-10 w-full rounded-md border border-outline-variant bg-white px-3 text-sm"
          >
            <option value="">Select a category...</option>
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
        ) : (
          <textarea
            value={ruleText}
            onChange={(e) => setRuleText(e.target.value)}
            placeholder="e.g. If you see 'internal' or 'for me', this is a personal transaction — do not add it to business income or expenses."
            rows={3}
            className="w-full rounded-md border border-outline-variant px-3 py-2 text-sm"
          />
        )}
        <Button type="submit" isLoading={createMutation.isPending}>
          Add Rule
        </Button>
      </form>
    </div>
  )
}
