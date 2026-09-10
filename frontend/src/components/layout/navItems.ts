export interface NavItem {
  to: string
  label: string
  icon: string
}

/** One canonical nav list used by both the desktop sidebar and the mobile bottom
 * bar — the mockups had inconsistent/missing nav across screens; this is the single
 * source of truth instead.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/ingestion', label: 'Ingestion', icon: 'upload_file' },
  { to: '/ledger', label: 'Ledger', icon: 'receipt_long' },
  { to: '/assets', label: 'Assets', icon: 'inventory_2' },
  { to: '/reports', label: 'Reports', icon: 'description' },
  { to: '/advisor', label: 'Advisor', icon: 'smart_toy' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
]
