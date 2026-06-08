"use client"

import { useState } from "react"

import { cn } from "@/lib/utils"

export type RangeKey = "24h" | "7d" | "30d" | "all"

const PRESETS: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "24h", label: "24h", days: 1 },
  { key: "7d", label: "7d", days: 7 },
  { key: "30d", label: "30d", days: 30 },
  { key: "all", label: "All", days: null },
]

export function sinceFor(key: RangeKey): string | undefined {
  const preset = PRESETS.find((p) => p.key === key)
  if (!preset?.days) return undefined
  return new Date(Date.now() - preset.days * 86_400_000).toISOString()
}

/** Time-range selector. Returns the selected key; callers derive `since`. */
export function useTimeRange(initial: RangeKey = "30d") {
  const [range, setRange] = useState<RangeKey>(initial)
  return { range, setRange, since: sinceFor(range) }
}

export function TimeRangePicker({
  value,
  onChange,
}: {
  value: RangeKey
  onChange: (k: RangeKey) => void
}) {
  return (
    <div className="inline-flex rounded-md border bg-card p-0.5">
      {PRESETS.map((p) => (
        <button
          key={p.key}
          onClick={() => onChange(p.key)}
          className={cn(
            "rounded px-3 py-1 text-xs font-medium transition-colors",
            value === p.key
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
