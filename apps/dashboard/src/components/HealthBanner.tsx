"use client"

import { usePoll } from "@/lib/usePoll"
import type { Health } from "@/types/api"

export function HealthBanner() {
  const { data, error } = usePoll<Health>("/api/v1/health", 15000)
  const ok = data?.database && !error
  if (ok) return null
  return (
    <div className="bg-destructive px-4 py-2 text-center text-sm text-white">
      API unreachable or database down — start the API:{" "}
      <code className="font-mono">uvicorn trading_api.app:app --port 8000</code>
    </div>
  )
}
