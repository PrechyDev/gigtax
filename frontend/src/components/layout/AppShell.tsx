import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileNav } from './MobileNav'
import { ProfileCompletionBanner } from '../ProfileCompletionBanner'

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-8 md:pb-8">
          <ProfileCompletionBanner />
          {children}
        </main>
      </div>
      <MobileNav />
    </div>
  )
}
