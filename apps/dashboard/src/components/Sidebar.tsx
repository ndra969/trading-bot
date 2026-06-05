"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  ListChecks,
  History,
  BarChart3,
  SlidersHorizontal,
  ShieldX,
} from "lucide-react"

import { cn } from "@/lib/utils"

const NAV = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Positions", href: "/positions", icon: ListChecks },
  { label: "History", href: "/history", icon: History },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Tuning", href: "/tuning", icon: SlidersHorizontal },
  { label: "Rejections", href: "/rejections", icon: ShieldX },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside
      className="flex h-screen flex-col bg-sidebar text-sidebar-foreground"
      style={{ width: "var(--sidebar-width)" }}
    >
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <div className="h-2.5 w-2.5 rounded-full bg-[hsl(var(--success))]" />
        <span className="font-semibold">Trading Bot</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {NAV.map(({ label, href, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-sidebar-hover text-sidebar-foreground"
                  : "text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          )
        })}
      </nav>
      <div className="border-t border-sidebar-border p-3 text-xs text-sidebar-muted">
        Read-only · tune in config/strategy_parameters.yaml
      </div>
    </aside>
  )
}
