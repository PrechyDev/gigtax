import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listCategories } from '../api/categories'
import { groupCategoriesForType } from '../lib/categoryLabels'
import { createManualTransaction } from '../api/transactions'
import { listStatements, retryLockedStatement, uploadStatements } from '../api/statements'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { PageSpinner, Spinner } from '../components/ui/Spinner'
import { StatusPill, parsingStatusTone } from '../components/ui/StatusPill'
import { PasswordField, SelectField, TextField } from '../components/ui/FormField'
import { ApiError } from '../lib/apiClient'
import { formatDateTime } from '../lib/formatters'

const IN_FLIGHT_STATUSES = new Set(['PENDING', 'PROCESSING'])
// Past this long still in flight, say so rather than let a spinner run silently —
// batches share the free-tier AI quota and can genuinely take longer during busy
// periods (see BATCH_STAGGER_SECONDS on the backend).
const SLOW_PROCESSING_THRESHOLD_MS = 15_000

function isTakingLonger(statement: { parsing_status: string; upload_date: string }): boolean {
  if (!IN_FLIGHT_STATUSES.has(statement.parsing_status)) return false
  return Date.now() - new Date(statement.upload_date).getTime() > SLOW_PROCESSING_THRESHOLD_MS
}

interface Toast {
  id: string
  message: string
  tone: 'success' | 'error' | 'neutral'
}

export function IngestionPage() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const retryInputRef = useRef<HTMLInputElement>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showManualEntry, setShowManualEntry] = useState(false)
  const [unlockTarget, setUnlockTarget] = useState<{ statementId: string; fileName: string } | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const previousStatusesRef = useRef<Map<string, string>>(new Map())
  const [, forceTick] = useState(0)

  const statementsQuery = useQuery({
    queryKey: ['statements'],
    queryFn: listStatements,
    // Processing now happens in the background (see backend core/background.py) —
    // poll while anything is still PENDING/PROCESSING so the queue below and the
    // completion toasts update on their own, no manual refresh needed.
    refetchInterval: (query) => (query.state.data?.some((s) => IN_FLIGHT_STATUSES.has(s.parsing_status)) ? 3000 : false),
  })

  // A poll whose response is byte-identical to the last one doesn't necessarily
  // trigger a re-render on its own — but "taking longer than usual" is purely a
  // function of elapsed time, not of the data changing, so tick independently of the
  // query while anything is still in flight.
  useEffect(() => {
    if (!statementsQuery.data?.some((s) => IN_FLIGHT_STATUSES.has(s.parsing_status))) return
    const interval = setInterval(() => forceTick((t) => t + 1), 3000)
    return () => clearInterval(interval)
  }, [statementsQuery.data])

  // Detects a file finishing (PROCESSING -> COMPLETED/FAILED/LOCKED) between polls
  // and surfaces a dismissible notification for it, independent of any other file
  // still uploading/processing at the same time.
  useEffect(() => {
    if (!statementsQuery.data) return
    const previous = previousStatusesRef.current
    const newToasts: Toast[] = []

    for (const statement of statementsQuery.data) {
      const prevStatus = previous.get(statement.statement_id)
      if (prevStatus && IN_FLIGHT_STATUSES.has(prevStatus) && statement.parsing_status !== prevStatus) {
        if (statement.parsing_status === 'COMPLETED') {
          newToasts.push(
            statement.transactions_created > 0
              ? {
                  id: `${statement.statement_id}-${Date.now()}`,
                  tone: 'success',
                  message: `"${statement.file_name}": ${statement.transactions_created} transaction(s) added.`,
                }
              : {
                  id: `${statement.statement_id}-${Date.now()}`,
                  tone: 'neutral',
                  message: `"${statement.file_name}" completed, but no transactions were found in it.`,
                },
          )
        } else if (statement.parsing_status === 'FAILED') {
          newToasts.push({
            id: `${statement.statement_id}-${Date.now()}`,
            tone: 'error',
            message: statement.error_message
              ? `"${statement.file_name}": ${statement.error_message}`
              : `"${statement.file_name}" failed to process. You can try uploading it again.`,
          })
        } else if (statement.parsing_status === 'LOCKED') {
          newToasts.push({
            id: `${statement.statement_id}-${Date.now()}`,
            tone: 'error',
            message: `"${statement.file_name}" is password-protected — unlock it below.`,
          })
        }
      }
    }

    if (newToasts.length > 0) setToasts((prev) => [...prev, ...newToasts])
    previousStatusesRef.current = new Map(statementsQuery.data.map((s) => [s.statement_id, s.parsing_status]))
  }, [statementsQuery.data])

  const uploadMutation = useMutation({
    mutationFn: uploadStatements,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statements'] })
    },
    onError: (err) => setUploadError(err instanceof ApiError ? err.message : 'Upload failed. Please try again.'),
  })

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploadError(null)
    uploadMutation.mutate(Array.from(files))
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragActive(false)
    handleFiles(e.dataTransfer.files)
  }

  function dismissToast(id: string) {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  function handleRetryFileChosen(e: ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files)
    e.target.value = '' // allow re-selecting the exact same file next time
  }

  return (
    <AppShell title="Data Ingestion">
      <p className="mb-6 text-on-surface-variant">Upload statements or manually enter records</p>

      {uploadError && (
        <div className="mb-4">
          <ErrorBanner message={uploadError} onDismiss={() => setUploadError(null)} />
        </div>
      )}

      {toasts.length > 0 && (
        <div className="mb-4 space-y-2">
          {toasts.map((toast) => {
            if (toast.tone === 'success') {
              return (
                <div key={toast.id} className="flex items-center gap-3">
                  <div className="flex-1">
                    <SuccessBanner message={toast.message} onDismiss={() => dismissToast(toast.id)} />
                  </div>
                  <Link to="/ledger" className="shrink-0 text-sm font-semibold text-accent hover:underline">
                    Review now
                  </Link>
                </div>
              )
            }
            if (toast.tone === 'neutral') {
              return (
                <div
                  key={toast.id}
                  className="flex items-start gap-3 rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3 text-on-surface-variant"
                >
                  <span className="material-symbols-outlined mt-0.5 shrink-0">info</span>
                  <p className="flex-1 text-sm">{toast.message}</p>
                  <button
                    onClick={() => dismissToast(toast.id)}
                    aria-label="Dismiss"
                    className="shrink-0 text-on-surface-variant/70"
                  >
                    <span className="material-symbols-outlined text-lg">close</span>
                  </button>
                </div>
              )
            }
            return <ErrorBanner key={toast.id} message={toast.message} onDismiss={() => dismissToast(toast.id)} />
          })}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragActive(true)
            }}
            onDragLeave={() => setIsDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
              isDragActive ? 'border-accent bg-accent/5' : 'border-outline-variant bg-surface-container-lowest'
            }`}
          >
            {uploadMutation.isPending ? (
              <Spinner size={32} />
            ) : (
              <span className="material-symbols-outlined text-4xl text-accent">cloud_upload</span>
            )}
            <p className="font-semibold text-navy">Drag & Drop files here</p>
            <p className="text-sm text-on-surface-variant">
              Supports PDF, CSV, Excel, and images (JPG/PNG) of handwritten notes
            </p>
            <Button type="button" variant="secondary" isLoading={uploadMutation.isPending}>
              Browse Files
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.csv,.xls,.xlsx,.jpg,.jpeg,.png"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>

          <div className="mt-6 rounded-lg bg-surface-container-lowest p-6 shadow-level-1">
            <h3 className="mb-4 font-semibold text-navy">Recent Uploads</h3>
            <input
              ref={retryInputRef}
              type="file"
              accept=".pdf,.csv,.xls,.xlsx,.jpg,.jpeg,.png"
              className="hidden"
              onChange={handleRetryFileChosen}
            />
            {statementsQuery.isLoading && <PageSpinner />}
            {statementsQuery.isError && (
              <ErrorBanner
                message="Could not load your uploads."
                onRetry={() => statementsQuery.refetch()}
              />
            )}
            {statementsQuery.data && statementsQuery.data.length === 0 && (
              <EmptyState icon="cloud_off" message="No recent uploads" />
            )}
            {statementsQuery.data && statementsQuery.data.length > 0 && (
              <ul className="divide-y divide-outline-variant">
                {statementsQuery.data.map((statement) => (
                  <li key={statement.statement_id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-on-surface">{statement.file_name}</p>
                      <p className="text-xs text-on-surface-variant">
                        {formatDateTime(statement.upload_date)}
                        {statement.parsing_status === 'COMPLETED' &&
                          ` · ${statement.transactions_created} transaction(s)`}
                      </p>
                      {statement.parsing_status === 'FAILED' && statement.error_message && (
                        <p className="mt-0.5 text-xs text-error">{statement.error_message}</p>
                      )}
                      {isTakingLonger(statement) && (
                        <p className="mt-0.5 text-xs text-on-surface-variant">
                          Still working — this can take longer during busy periods.
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {statement.parsing_status === 'PROCESSING' && <Spinner size={16} />}
                      <StatusPill label={statement.parsing_status} tone={parsingStatusTone(statement.parsing_status)} />
                      {statement.parsing_status === 'LOCKED' && (
                        <Button
                          variant="secondary"
                          onClick={() =>
                            setUnlockTarget({ statementId: statement.statement_id, fileName: statement.file_name })
                          }
                        >
                          Unlock
                        </Button>
                      )}
                      {statement.parsing_status === 'FAILED' && (
                        <Button variant="secondary" onClick={() => retryInputRef.current?.click()}>
                          Retry
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="rounded-lg bg-accent p-6 text-bg shadow-level-1">
          <h3 className="mb-2 font-semibold">Manual Entry</h3>
          <p className="mb-4 text-sm opacity-70">
            Prefer to type it in yourself? Add a single income or expense record directly.
          </p>
          <Button variant="secondary" onClick={() => setShowManualEntry(true)}>
            Add Record
          </Button>
        </div>
      </div>

      {showManualEntry && (
        <ManualEntryModal
          onClose={() => setShowManualEntry(false)}
          onSaved={() => {
            setShowManualEntry(false)
            queryClient.invalidateQueries({ queryKey: ['transactions'] })
          }}
        />
      )}

      {unlockTarget && (
        <UnlockModal target={unlockTarget} onClose={() => setUnlockTarget(null)} />
      )}
    </AppShell>
  )
}

function ManualEntryModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const [form, setForm] = useState({
    transaction_type: 'expense' as 'income' | 'expense',
    date: new Date().toISOString().slice(0, 10),
    amount: '',
    description: '',
    category_slug: '',
  })
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: createManualTransaction,
    onSuccess: onSaved,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not save this record.'),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    mutation.mutate({
      transaction_type: form.transaction_type,
      date: new Date(form.date).toISOString(),
      amount: Number(form.amount),
      description: form.description,
      category_slug: form.category_slug || undefined,
    })
  }

  return (
    <Modal title="Manual Entry" onClose={onClose}>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <SelectField
          label="Type"
          value={form.transaction_type}
          onChange={(e) =>
            setForm({ ...form, transaction_type: e.target.value as 'income' | 'expense', category_slug: '' })
          }
        >
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </SelectField>
        <TextField
          label="Date"
          type="date"
          required
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
        />
        <TextField
          label="Amount (NGN)"
          type="number"
          required
          min={0}
          step="0.01"
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
        />
        <TextField
          label="Description"
          required
          maxLength={500}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <SelectField
          label="Category"
          value={form.category_slug}
          onChange={(e) => setForm({ ...form, category_slug: e.target.value })}
        >
          <option value="">Select a category...</option>
          {groupCategoriesForType(categoriesQuery.data ?? [], form.transaction_type).map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.categories.map((c) => (
                <option key={c.developer_slug} value={c.developer_slug}>
                  {c.category_name}
                </option>
              ))}
            </optgroup>
          ))}
        </SelectField>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={mutation.isPending}>
            Save Record
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function UnlockModal({
  target,
  onClose,
}: {
  target: { statementId: string; fileName: string }
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => retryLockedStatement(target.statementId, file as File, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statements'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      onClose()
    },
    onError: (err) =>
      setError(
        err instanceof ApiError && err.status === 423
          ? 'Incorrect password. Please try again.'
          : err instanceof ApiError
            ? err.message
            : 'Could not unlock this file.',
      ),
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!file) {
      setError('Please re-select the file — it was never stored on our server, only processed in memory.')
      return
    }
    mutation.mutate()
  }

  return (
    <Modal title={`Unlock "${target.fileName}"`} onClose={onClose}>
      <p className="mb-4 text-sm text-on-surface-variant">
        This file is password-protected. Please re-select it and enter the password to continue.
      </p>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="file"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm"
        />
        <PasswordField
          label="Password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={mutation.isPending}>
            Unlock
          </Button>
        </div>
      </form>
    </Modal>
  )
}
