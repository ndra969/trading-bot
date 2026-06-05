"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { apiFetch } from "@/lib/api"

export interface PollState<T> {
  data: T | null
  error: string | null
  loading: boolean
  refresh: () => void
}

/**
 * Poll an API path on an interval (tiered: live 3s, history 15s, analytics 60s).
 * Pass intervalMs=0 to fetch once (manual refresh only).
 */
export function usePoll<T>(path: string | null, intervalMs = 0): PollState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const pathRef = useRef(path)
  pathRef.current = path

  const load = useCallback(async () => {
    const p = pathRef.current
    if (!p) return
    try {
      const d = await apiFetch<T>(p)
      setData(d)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "request failed")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load()
    if (intervalMs > 0) {
      const id = setInterval(load, intervalMs)
      return () => clearInterval(id)
    }
  }, [load, intervalMs, path])

  return { data, error, loading, refresh: load }
}
