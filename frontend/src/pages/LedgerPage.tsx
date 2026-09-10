import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listCategories, type Category } from '../api/categories'
import { groupCategoriesForType } from '../lib/categoryLabels'
import {
  deleteTransaction,
  listTransactions,
  reviewTransaction,
  type Transaction,
  type TransactionReviewInput,
} from '../api/transactions'
import { listReceipts, uploadReceipt } from '../api/receipts'
import { createCustomRule } from '../api/customRules'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { ErrorBanner, SuccessBanner } from '../components/ui/Banner'
import { EmptyState } from '../components/ui/EmptyState'
import { PageSpinner, Spinner } from '../components/ui/Spinner'
import { StatusPill, reviewStatusTone } from '../components/ui/StatusPill'
import { ApiError } from '../lib/apiClient'
import { formatDate, formatNaira } from '../lib/formatters'

const LOW_CONFIDENCE_THRESHOLD = 0.6

export function LedgerPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const transactionsQuery = useQuery({
    queryKey: ['transactions', statusFilter],
    queryFn: () => listTransactions(statusFilter ? { review_status: statusFilter } : {}),
  })
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategories })

  const reviewMutation = useMutation({
    mutationFn: ({ id, ...input }: { id: string } & TransactionReviewInput) => reviewTransaction(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not update this transaction.'),
  })

  const createRuleMutation = useMutation({
    mutationFn: createCustomRule,
    onSuccess: () => setSuccess('Rule created — future matching transactions will use it automatically.'),
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not create the rule.'),
  })

  const bulkApproveMutation = useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map((id) => reviewTransaction(id, { review_status: 'APPROVED' }))),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setSelectedIds(new Set())
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not approve the selected transactions.'),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map((id) => deleteTransaction(id))),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      setSelectedIds(new Set())
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not delete the selected transactions.'),
  })

  function categoryFor(transaction: Transaction) {
    const id = transaction.user_category_id ?? transaction.ai_category_id
    return categoriesQuery.data?.find((c) => c.category_id === id)
  }

  function toggleOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const rows = transactionsQuery.data ?? []
  const allSelected = rows.length > 0 && rows.every((t) => selectedIds.has(t.transaction_id))

  function toggleAll() {
    setSelectedIds(allSelected ? new Set() : new Set(rows.map((t) => t.transaction_id)))
  }

  function handleBulkDelete() {
    const ids = Array.from(selectedIds)
    if (window.confirm(`Delete ${ids.length} transaction(s)? This cannot be undone.`)) {
      bulkDeleteMutation.mutate(ids)
    }
  }

  return (
    <AppShell title="Ledger Review">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-on-surface-variant">Review and confirm AI-categorized transactions.</p>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setSelectedIds(new Set())
          }}
          className="h-10 rounded-lg border border-outline-variant bg-white px-3 text-sm"
        >
          <option value="">All statuses</option>
          <option value="PENDING">Pending review</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}
      {success && (
        <div className="mb-4">
          <SuccessBanner message={success} onDismiss={() => setSuccess(null)} />
        </div>
      )}

      {selectedIds.size > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-lg bg-navy px-4 py-3 text-white shadow-level-1">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <button
            onClick={() => bulkApproveMutation.mutate(Array.from(selectedIds))}
            disabled={bulkApproveMutation.isPending || bulkDeleteMutation.isPending}
            className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold hover:bg-white/20 disabled:opacity-50"
          >
            {bulkApproveMutation.isPending && <Spinner size={14} />}
            Approve Selected
          </button>
          <button
            onClick={handleBulkDelete}
            disabled={bulkApproveMutation.isPending || bulkDeleteMutation.isPending}
            className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-error hover:bg-white/20 disabled:opacity-50"
          >
            {bulkDeleteMutation.isPending && <Spinner size={14} />}
            Delete Selected
          </button>
          <button onClick={() => setSelectedIds(new Set())} className="ml-auto text-sm text-white/70 hover:text-white">
            Cancel
          </button>
        </div>
      )}

      {transactionsQuery.isLoading && <PageSpinner />}
      {transactionsQuery.isError && (
        <ErrorBanner message="Could not load your transactions." onRetry={() => transactionsQuery.refetch()} />
      )}
      {transactionsQuery.data && transactionsQuery.data.length === 0 && (
        <EmptyState icon="receipt_long" message="No transactions yet — upload a statement or add one manually." />
      )}

      {transactionsQuery.data && transactionsQuery.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg bg-surface-container-lowest shadow-level-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant text-left text-xs font-semibold uppercase text-on-surface-variant">
                <th className="w-10 px-4 py-3">
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Select all" />
                </th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3 tabular-nums">Amount</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Receipt</th>
              </tr>
            </thead>
            <tbody>
              {transactionsQuery.data.map((transaction) => (
                <TransactionRow
                  key={transaction.transaction_id}
                  transaction={transaction}
                  category={categoryFor(transaction)}
                  categories={categoriesQuery.data ?? []}
                  homeOfficeEnabled={!!user?.has_home_office}
                  isSelected={selectedIds.has(transaction.transaction_id)}
                  onToggleSelect={() => toggleOne(transaction.transaction_id)}
                  onReview={(input) => reviewMutation.mutate({ id: transaction.transaction_id, ...input })}
                  onCreateRule={(pattern, categorySlug) =>
                    createRuleMutation.mutate({ keyword_pattern: pattern, assigned_category: categorySlug })
                  }
                  isSaving={reviewMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  )
}

function TransactionRow({
  transaction,
  category,
  categories,
  isSelected,
  onToggleSelect,
  onReview,
  onCreateRule,
  isSaving,
}: {
  transaction: Transaction
  category?: { developer_slug: string; category_name: string }
  categories: Category[]
  homeOfficeEnabled: boolean
  isSelected: boolean
  onToggleSelect: () => void
  onReview: (input: TransactionReviewInput) => void
  onCreateRule: (pattern: string, categorySlug: string) => void
  isSaving: boolean
}) {
  const [receiptsOpen, setReceiptsOpen] = useState(false)
  const [isEditingDescription, setIsEditingDescription] = useState(false)
  const [descriptionDraft, setDescriptionDraft] = useState(transaction.description)
  const isLowConfidence =
    transaction.confidence_score !== null && transaction.confidence_score < LOW_CONFIDENCE_THRESHOLD

  function saveDescription() {
    setIsEditingDescription(false)
    const trimmed = descriptionDraft.trim()
    if (trimmed && trimmed !== transaction.description) {
      onReview({ description: trimmed })
    } else {
      setDescriptionDraft(transaction.description)
    }
  }

  return (
    <>
      <tr className={`border-b border-outline-variant last:border-0 ${isSelected ? 'bg-blue/5' : ''}`}>
        <td className="px-4 py-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggleSelect}
            aria-label={`Select transaction: ${transaction.description}`}
          />
        </td>
        <td className="whitespace-nowrap px-4 py-3">{formatDate(transaction.date)}</td>
        <td className="px-4 py-3">
          {isEditingDescription ? (
            <input
              autoFocus
              value={descriptionDraft}
              onChange={(e) => setDescriptionDraft(e.target.value)}
              onBlur={saveDescription}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveDescription()
                if (e.key === 'Escape') {
                  setDescriptionDraft(transaction.description)
                  setIsEditingDescription(false)
                }
              }}
              className="h-8 w-full rounded-md border border-blue px-2 text-sm"
            />
          ) : (
            <button
              className="text-left hover:underline"
              onClick={() => setIsEditingDescription(true)}
              title="Click to rename"
            >
              {transaction.description}
            </button>
          )}
          <p className="text-xs text-on-surface-variant">{transaction.source}</p>
        </td>
        <td
          className={`whitespace-nowrap px-4 py-3 tabular-nums font-medium ${
            transaction.type === 'income' ? 'text-emerald-dark' : 'text-navy'
          }`}
        >
          {transaction.type === 'income' ? '+' : '-'}
          {formatNaira(transaction.amount)}
        </td>
        <td className="px-4 py-3">
          <select
            defaultValue={category?.developer_slug ?? ''}
            onChange={(e) => onReview({ category_slug: e.target.value })}
            className={`h-9 rounded-md border bg-white px-2 text-xs ${
              isLowConfidence ? 'border-error text-error' : 'border-outline-variant'
            }`}
          >
            <option value="" disabled>
              Select a category...
            </option>
            {groupCategoriesForType(categories, transaction.type).map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.categories.map((c) => (
                  <option key={c.developer_slug} value={c.developer_slug}>
                    {c.category_name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          {isLowConfidence && <p className="mt-1 text-xs text-error">AI confidence low — please verify</p>}
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <StatusPill label={transaction.review_status} tone={reviewStatusTone(transaction.review_status)} />
            {transaction.review_status !== 'APPROVED' && (
              <button
                disabled={isSaving}
                onClick={() => onReview({ review_status: 'APPROVED' })}
                className="text-emerald-dark hover:underline disabled:opacity-50"
              >
                Approve
              </button>
            )}
            {isSaving && <Spinner size={14} />}
          </div>
          {category && (
            <button
              className="mt-1 text-xs text-blue hover:underline"
              onClick={() => {
                const keyword = window.prompt(
                  `Always categorize transactions matching which keyword as "${category.category_name}"?`,
                  transaction.description.split(' ')[0],
                )
                if (keyword) onCreateRule(keyword, category.developer_slug)
              }}
            >
              + Create a rule from this
            </button>
          )}
        </td>
        <td className="px-4 py-3">
          {transaction.type === 'expense' ? (
            <button className="text-blue hover:underline" onClick={() => setReceiptsOpen((v) => !v)}>
              Receipts
            </button>
          ) : (
            <span className="text-on-surface-variant">N/A</span>
          )}
        </td>
      </tr>
      {receiptsOpen && (
        <tr>
          <td colSpan={7} className="bg-surface-container-low px-4 py-3">
            <ReceiptsPanel transactionId={transaction.transaction_id} />
          </td>
        </tr>
      )}
    </>
  )
}

function ReceiptsPanel({ transactionId }: { transactionId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const receiptsQuery = useQuery({
    queryKey: ['receipts', transactionId],
    queryFn: () => listReceipts(transactionId),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadReceipt(transactionId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['receipts', transactionId] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not upload this receipt.'),
  })

  if (!user?.google_drive_connected) {
    return (
      <p className="text-sm text-on-surface-variant">
        Connect Google Drive in Settings to attach receipts to transactions.
      </p>
    )
  }

  return (
    <div>
      {error && (
        <div className="mb-2">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}
      {receiptsQuery.isLoading && <Spinner size={16} />}
      {receiptsQuery.data && receiptsQuery.data.length === 0 && (
        <p className="text-sm italic text-on-surface-variant">No receipts attached.</p>
      )}
      {receiptsQuery.data && receiptsQuery.data.length > 0 && (
        <ul className="mb-2 space-y-1 text-sm">
          {receiptsQuery.data.map((r) => (
            <li key={r.receipt_id}>{r.file_type ?? 'file'} — uploaded {formatDate(r.upload_date)}</li>
          ))}
        </ul>
      )}
      <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-blue">
        {uploadMutation.isPending ? <Spinner size={14} /> : <span className="material-symbols-outlined text-lg">add</span>}
        Upload receipt
        <input
          type="file"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) uploadMutation.mutate(file)
          }}
        />
      </label>
    </div>
  )
}
