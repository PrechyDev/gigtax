import { useState } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { listCategories, type Category } from '../api/categories'
import { groupCategoriesForType } from '../lib/categoryLabels'
import {
  bulkDeleteTransactions,
  bulkReviewTransactions,
  deleteTransaction,
  listTransactions,
  reviewTransaction,
  type Transaction,
  type TransactionFilters,
  type TransactionReviewInput,
} from '../api/transactions'
import { listReceipts, uploadReceipt } from '../api/receipts'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../components/layout/AppShell'
import { ErrorBanner } from '../components/ui/Banner'
import { EmptyState } from '../components/ui/EmptyState'
import { PageSpinner, Spinner } from '../components/ui/Spinner'
import { StatusPill, reviewStatusTone } from '../components/ui/StatusPill'
import { ApiError } from '../lib/apiClient'
import { formatDate, formatNaira } from '../lib/formatters'

const LOW_CONFIDENCE_THRESHOLD = 0.6
// The AI pipeline force-categorizes personal/non-business transactions into this
// slug (see backend/modules/ai_categorization/categorization.py, instructions #5/#6)
// rather than omitting them — the Uncategorized bucket below filters down to exactly
// these, so a user can skim and either recategorize (real business, rescued) or
// discard (really personal) without them being buried among ordinary pending items.
const UNCATEGORIZED_CATEGORY_SLUG = 'uncategorized'
const DISCARD_RETENTION_DAYS = 30

// Every transaction lives in exactly one of these four — a strict partition, not an
// overlapping set of views like the old flat tab list (All/Pending/Income/Expense/
// Needs Attention/Discarded) was:
//   Approved         review_status = APPROVED
//   Pending Review   review_status = PENDING   and NOT uncategorized
//   Uncategorized    review_status = PENDING   and IS uncategorized
//   Discarded        review_status = REJECTED
// Income/Expense is a second, independent dimension — only offered as a sub-filter on
// Approved and Pending Review, where volume is high enough to need it; Uncategorized
// and Discarded are small enough that "just show me everything in here" is enough.
type LedgerBucket = 'approved' | 'pending' | 'uncategorized' | 'discarded'
type TypeFilter = 'all' | 'income' | 'expense'

const LEDGER_BUCKETS: { id: LedgerBucket; label: string }[] = [
  { id: 'approved', label: 'Approved' },
  { id: 'pending', label: 'Pending Review' },
  { id: 'uncategorized', label: 'Uncategorized' },
  { id: 'discarded', label: 'Discarded' },
]

const TYPE_FILTERS: { id: TypeFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'income', label: 'Income' },
  { id: 'expense', label: 'Expenses' },
]

// Only these two buckets support the Income/Expenses sub-filter.
function bucketHasTypeFilter(bucket: LedgerBucket): boolean {
  return bucket === 'approved' || bucket === 'pending'
}

function filtersForBucket(bucket: LedgerBucket, typeFilter: TypeFilter): TransactionFilters {
  const typeFilterParam: TransactionFilters =
    bucketHasTypeFilter(bucket) && typeFilter !== 'all' ? { transaction_type: typeFilter } : {}

  if (bucket === 'approved') return { review_status: 'APPROVED', ...typeFilterParam }
  if (bucket === 'pending') return { review_status: 'PENDING', exclude_uncategorized: true, ...typeFilterParam }
  if (bucket === 'uncategorized') return { review_status: 'PENDING', category_slug: UNCATEGORIZED_CATEGORY_SLUG }
  return { review_status: 'REJECTED' }
}

function autoDeleteDate(discardedAt: string): string {
  const date = new Date(discardedAt)
  date.setDate(date.getDate() + DISCARD_RETENTION_DAYS)
  return formatDate(date.toISOString())
}

const PAGE_SIZE = 50
const VALID_BUCKETS = new Set(LEDGER_BUCKETS.map((t) => t.id))

function isLedgerBucket(value: string | null): value is LedgerBucket {
  return value !== null && VALID_BUCKETS.has(value as LedgerBucket)
}

export function LedgerPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  // Lets the dashboard's "N awaiting your review" / "N flagged as personal" links land
  // straight on the right bucket (/ledger?tab=pending, ?tab=uncategorized) instead of
  // just the page in its default state.
  const [bucket, setBucket] = useState<LedgerBucket>(() => {
    const fromUrl = searchParams.get('tab')
    return isLedgerBucket(fromUrl) ? fromUrl : 'pending'
  })
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const isDiscardedTab = bucket === 'discarded'
  const [error, setError] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const transactionsQuery = useInfiniteQuery({
    queryKey: ['transactions', bucket, typeFilter],
    queryFn: ({ pageParam }) =>
      listTransactions({ ...filtersForBucket(bucket, typeFilter), limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => (lastPage.length === PAGE_SIZE ? allPages.length * PAGE_SIZE : undefined),
  })
  const rows = transactionsQuery.data?.pages.flat() ?? []
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: listCategories })

  function invalidateAfterChange() {
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    queryClient.invalidateQueries({ queryKey: ['assets'] })
    setSelectedIds(new Set())
  }

  const reviewMutation = useMutation({
    mutationFn: ({ id, ...input }: { id: string } & TransactionReviewInput) => reviewTransaction(id, input),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not update this transaction.'),
  })

  const bulkApproveMutation = useMutation({
    mutationFn: (ids: string[]) => bulkReviewTransactions(ids, 'APPROVED'),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not approve the selected transactions.'),
  })

  const bulkDiscardMutation = useMutation({
    mutationFn: (ids: string[]) => bulkReviewTransactions(ids, 'REJECTED'),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not discard the selected transactions.'),
  })

  const bulkRestoreMutation = useMutation({
    mutationFn: (ids: string[]) => bulkReviewTransactions(ids, 'PENDING'),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not restore the selected transactions.'),
  })

  const bulkHardDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => bulkDeleteTransactions(ids),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not delete the selected transactions.'),
  })

  const deleteOneMutation = useMutation({
    mutationFn: (id: string) => deleteTransaction(id),
    onSuccess: invalidateAfterChange,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Could not delete this transaction.'),
  })

  function handleDeleteOne(transaction: Transaction) {
    if (
      window.confirm(
        `Permanently delete "${transaction.description}"? Any linked capital asset will be removed too. This cannot be undone.`,
      )
    ) {
      deleteOneMutation.mutate(transaction.transaction_id)
    }
  }

  function handleBulkHardDelete() {
    const ids = Array.from(selectedIds)
    if (
      window.confirm(
        `Permanently delete ${ids.length} transaction(s)? Any linked capital assets will be removed too. This cannot be undone.`,
      )
    ) {
      bulkHardDeleteMutation.mutate(ids)
    }
  }

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

  const allSelected = rows.length > 0 && rows.every((t) => selectedIds.has(t.transaction_id))

  function toggleAll() {
    setSelectedIds(allSelected ? new Set() : new Set(rows.map((t) => t.transaction_id)))
  }

  const isBulkActionPending =
    bulkApproveMutation.isPending ||
    bulkDiscardMutation.isPending ||
    bulkRestoreMutation.isPending ||
    bulkHardDeleteMutation.isPending

  return (
    <AppShell title="Ledger Review">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-on-surface-variant">Review and confirm AI-categorized transactions.</p>
        <div className="flex flex-wrap gap-1 rounded-lg bg-surface-container-low p-1">
          {LEDGER_BUCKETS.map((b) => (
            <button
              key={b.id}
              onClick={() => {
                setBucket(b.id)
                setSelectedIds(new Set())
              }}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                bucket === b.id
                  ? 'bg-surface-container-lowest text-blue-dark shadow-level-1'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {bucketHasTypeFilter(bucket) && (
        <div className="mb-4 flex gap-1 rounded-lg bg-surface-container-low p-1 text-sm w-fit">
          {TYPE_FILTERS.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setTypeFilter(t.id)
                setSelectedIds(new Set())
              }}
              className={`rounded-md px-3 py-1 font-medium transition-colors ${
                typeFilter === t.id
                  ? 'bg-surface-container-lowest text-blue-dark shadow-level-1'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {bucket === 'uncategorized' && (
        <p className="mb-4 text-sm text-on-surface-variant">
          These were flagged as personal or unclear and left out of your tax calculation. Pick a real category to
          bring one back into your business records, or discard it if it really is personal.
        </p>
      )}
      {isDiscardedTab && (
        <p className="mb-4 text-sm text-on-surface-variant">
          Discarded transactions stay here for {DISCARD_RETENTION_DAYS} days before they're permanently deleted —
          restore one if you discarded it by mistake, or delete it now to skip the wait.
        </p>
      )}

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {selectedIds.size > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg bg-navy px-4 py-3 text-white shadow-level-1">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          {isDiscardedTab ? (
            <>
              <button
                onClick={() => bulkRestoreMutation.mutate(Array.from(selectedIds))}
                disabled={isBulkActionPending}
                className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold hover:bg-white/20 disabled:opacity-50"
              >
                {bulkRestoreMutation.isPending && <Spinner size={14} />}
                Restore Selected
              </button>
              <button
                onClick={handleBulkHardDelete}
                disabled={isBulkActionPending}
                className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-error hover:bg-white/20 disabled:opacity-50"
              >
                {bulkHardDeleteMutation.isPending && <Spinner size={14} />}
                Delete Permanently
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => bulkApproveMutation.mutate(Array.from(selectedIds))}
                disabled={isBulkActionPending}
                className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold hover:bg-white/20 disabled:opacity-50"
              >
                {bulkApproveMutation.isPending && <Spinner size={14} />}
                Approve Selected
              </button>
              <button
                onClick={() => bulkDiscardMutation.mutate(Array.from(selectedIds))}
                disabled={isBulkActionPending}
                className="flex items-center gap-1 rounded-md bg-white/10 px-3 py-1.5 text-sm font-semibold text-error hover:bg-white/20 disabled:opacity-50"
              >
                {bulkDiscardMutation.isPending && <Spinner size={14} />}
                Discard Selected
              </button>
            </>
          )}
          <button onClick={() => setSelectedIds(new Set())} className="ml-auto text-sm text-white/70 hover:text-white">
            Cancel
          </button>
        </div>
      )}

      {transactionsQuery.isLoading && <PageSpinner />}
      {transactionsQuery.isError && (
        <ErrorBanner message="Could not load your transactions." onRetry={() => transactionsQuery.refetch()} />
      )}
      {!transactionsQuery.isLoading && rows.length === 0 && (
        <EmptyState
          icon="receipt_long"
          message={
            isDiscardedTab
              ? 'Nothing discarded — items you discard show up here for 30 days before being deleted.'
              : 'No transactions yet — upload a statement or add one manually.'
          }
          action={{ label: 'Go to Ingestion', onClick: () => navigate('/ingestion') }}
        />
      )}

      {rows.length > 0 && (
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
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {rows.map((transaction) => (
                <TransactionRow
                  key={transaction.transaction_id}
                  transaction={transaction}
                  category={categoryFor(transaction)}
                  categories={categoriesQuery.data ?? []}
                  isDiscardedTab={isDiscardedTab}
                  isSelected={selectedIds.has(transaction.transaction_id)}
                  onToggleSelect={() => toggleOne(transaction.transaction_id)}
                  onReview={(input) => reviewMutation.mutate({ id: transaction.transaction_id, ...input })}
                  onHardDelete={() => handleDeleteOne(transaction)}
                  isSaving={reviewMutation.isPending}
                  isDeleting={deleteOneMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {transactionsQuery.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={() => transactionsQuery.fetchNextPage()}
            disabled={transactionsQuery.isFetchingNextPage}
            className="flex items-center gap-2 rounded-lg border border-outline-variant px-4 py-2 text-sm font-medium text-on-surface-variant hover:bg-surface-container-low disabled:opacity-50"
          >
            {transactionsQuery.isFetchingNextPage && <Spinner size={14} />}
            Load more
          </button>
        </div>
      )}
    </AppShell>
  )
}

function TransactionRow({
  transaction,
  category,
  categories,
  isDiscardedTab,
  isSelected,
  onToggleSelect,
  onReview,
  onHardDelete,
  isSaving,
  isDeleting,
}: {
  transaction: Transaction
  category?: { developer_slug: string; category_name: string }
  categories: Category[]
  isDiscardedTab: boolean
  isSelected: boolean
  onToggleSelect: () => void
  onReview: (input: TransactionReviewInput) => void
  onHardDelete: () => void
  isSaving: boolean
  isDeleting: boolean
}) {
  const [isEditingDescription, setIsEditingDescription] = useState(false)
  const [descriptionDraft, setDescriptionDraft] = useState(transaction.description)
  // Only a nudge to check an untouched AI guess before acting on it — once the user
  // has approved, discarded, or picked a category themselves, confidence_score is
  // stale history, not a live concern, so the warning must not outlive the action.
  const isLowConfidence =
    transaction.review_status === 'PENDING' &&
    transaction.user_category_id === null &&
    transaction.confidence_score !== null &&
    transaction.confidence_score < LOW_CONFIDENCE_THRESHOLD
  // "uncategorized" isn't a selectable option in groupCategoriesForType (it's the AI's
  // personal/unclear fallback, not a real business category — see UNCATEGORIZED_CATEGORY_SLUG
  // above), so treating it as "a category is selected" would pre-fill the dropdown with
  // whatever option happens to render first, silently misrepresenting the transaction as
  // already categorized. Every row in the Uncategorized bucket hits this, so it must
  // resolve to "nothing selected" instead.
  const isUncategorized = category?.developer_slug === UNCATEGORIZED_CATEGORY_SLUG
  const selectableCategory = category && !isUncategorized ? category : undefined

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
              className="flex items-center gap-1.5 text-left hover:underline"
              onClick={() => setIsEditingDescription(true)}
              title="Rename"
            >
              {transaction.description}
              <span className="material-symbols-outlined shrink-0 text-sm text-on-surface-variant">edit</span>
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
            defaultValue={selectableCategory?.developer_slug ?? ''}
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
            {isSaving && <Spinner size={14} />}
          </div>
          {isDiscardedTab && transaction.discarded_at && (
            <p className="mt-1 text-xs text-on-surface-variant">
              Discarded {formatDate(transaction.discarded_at)} — auto-deletes {autoDeleteDate(transaction.discarded_at)}
            </p>
          )}
          <div className="mt-1 flex items-center gap-2 text-xs">
            {isDiscardedTab ? (
              <button
                disabled={isSaving}
                onClick={() => onReview({ review_status: 'PENDING' })}
                className="text-emerald-dark hover:underline disabled:opacity-50"
              >
                Restore
              </button>
            ) : (
              <>
                {transaction.review_status !== 'APPROVED' && (
                  <button
                    disabled={isSaving}
                    onClick={() => onReview({ review_status: 'APPROVED' })}
                    className="text-emerald-dark hover:underline disabled:opacity-50"
                  >
                    Approve
                  </button>
                )}
                {transaction.review_status !== 'REJECTED' && (
                  <button
                    disabled={isSaving}
                    onClick={() => onReview({ review_status: 'REJECTED' })}
                    className="text-on-surface-variant hover:underline disabled:opacity-50"
                  >
                    Discard
                  </button>
                )}
              </>
            )}
          </div>
        </td>
        <td className="px-4 py-3">
          <ReceiptCell transactionId={transaction.transaction_id} />
        </td>
        <td className="px-4 py-3">
          {isDiscardedTab && (
            <button
              onClick={onHardDelete}
              disabled={isDeleting}
              aria-label="Delete permanently"
              title="Delete permanently"
              className="text-on-surface-variant hover:text-error disabled:opacity-50"
            >
              {isDeleting ? <Spinner size={16} /> : <span className="material-symbols-outlined text-lg">delete_forever</span>}
            </button>
          )}
        </td>
      </tr>
    </>
  )
}

/** A single compact cell, not an expand-to-see-more panel: no receipt shows "No
 * receipt" plus a small add control; one or more receipts show the most recent as a
 * direct link straight to that file in Google Drive (BYOS — storage_path is the
 * Drive file id, so this is exactly what opens it, no intermediate page needed).
 */
function ReceiptCell({ transactionId }: { transactionId: string }) {
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
      <Link
        to="/settings"
        className="text-xs text-on-surface-variant hover:text-blue hover:underline"
        title="Connect Google Drive in Settings to attach receipts"
      >
        Connect Drive
      </Link>
    )
  }

  if (receiptsQuery.isLoading) return <Spinner size={14} />

  const receipts = receiptsQuery.data ?? []
  const mostRecent = receipts.length
    ? [...receipts].sort((a, b) => new Date(b.upload_date).getTime() - new Date(a.upload_date).getTime())[0]
    : null

  return (
    <div className="flex items-center gap-1.5">
      {mostRecent ? (
        <a
          href={`https://drive.google.com/file/d/${mostRecent.storage_path}/view`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue hover:underline"
          title={`Uploaded ${formatDate(mostRecent.upload_date)}`}
        >
          <span className="material-symbols-outlined text-base">description</span>
          Receipt{receipts.length > 1 ? ` (${receipts.length})` : ''}
        </a>
      ) : (
        <span className="text-xs text-on-surface-variant">No receipt</span>
      )}
      <label
        className="cursor-pointer text-on-surface-variant hover:text-blue"
        title={mostRecent ? 'Attach another receipt' : 'Attach a receipt (recommended, not required)'}
      >
        {uploadMutation.isPending ? (
          <Spinner size={14} />
        ) : (
          <span className="material-symbols-outlined align-middle text-base">add_circle</span>
        )}
        <input
          type="file"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) uploadMutation.mutate(file)
          }}
        />
      </label>
      {error && <span className="text-xs text-error" title={error}>⚠</span>}
    </div>
  )
}
