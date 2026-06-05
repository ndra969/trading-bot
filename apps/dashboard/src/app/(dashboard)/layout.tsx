import { HealthBanner } from "@/components/HealthBanner"
import { Sidebar } from "@/components/Sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex h-screen flex-1 flex-col overflow-hidden">
        <HealthBanner />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
