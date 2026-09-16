export interface NavItem {
  to: string
  label: string
  icon: string
}

/** One canonical nav list used by both the desktop sidebar and the mobile bottom
 * bar — the mockups had inconsistent/missing nav across screens; this is the single
 * source of truth instead.
 */
export const PRIMARY_NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { to: '/ingestion', label: 'Add', icon: 'upload_file' },
  { to: '/ledger', label: 'Ledger', icon: 'receipt_long' },
  { to: '/reports', label: 'Reports', icon: 'summarize' },
]

export const SECONDARY_NAV_ITEMS = [
  { to: '/assets', label: 'Assets', icon: 'inventory_2' },
  { to: '/advisor', label: 'Advisor', icon: 'smart_toy' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
]

// For desktop sidebar which shows all of them:
export const NAV_ITEMS = [...PRIMARY_NAV_ITEMS, ...SECONDARY_NAV_ITEMS]
