/** The one loading pattern used everywhere — inline in a button, or centered as a
 * page-level loader. Matches the single spinner style found in the Stitch mockups
 * (upload_manual_entry's "Processing..." row) rather than inventing a new one.
 */
export function Spinner({ size = 20, className = '' }: { size?: number; className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block animate-spin rounded-full border-2 border-accent border-t-transparent ${className}`}
      style={{ width: size, height: size }}
    />
  )
}

export function PageSpinner() {
  return (
    <div className="flex h-64 w-full items-center justify-center">
      <Spinner size={32} />
    </div>
  )
}
