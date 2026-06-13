"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { apiFetch } from "@/lib/api"

export interface PollState<T> {
  data: T | null
  error: string | null
  loading: boolean
  refresh: () => void
}

/** Stop auto-polling after this many consecutive failures (manual refresh resumes). */
const MAX_CONSECUTIVE_FAILURES = 5

/**
 * Poll an API path on an interval (tiered: live 3s, history 15s, analytics 60s).
 * Pass intervalMs=0 to fetch once (manual refresh only).
 *
 * After {@link MAX_CONSECUTIVE_FAILURES} consecutive errors the interval is
 * cleared so a broken endpoint isn't hammered forever; the last error stays
 * visible and calling `refresh()` resets the counter and resumes polling.
 */
export function usePoll<T>(path: string | null, intervalMs = 0): PollState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const pathRef = useRef(path)
  pathRef.current = path

  const failuresRef = useRef(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const load = useCallback(async () => {
    const p = pathRef.current
    if (!p) return
    try {
      const d = await apiFetch<T>(p)
      setData(d)
      setError(null)
      failuresRef.current = 0
    } catch (e) {
      failuresRef.current += 1
      setError(e instanceof Error ? e.message : "request failed")
      if (failuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        stopPolling()
      }
    } finally {
      setLoading(false)
    }
  }, [stopPolling])

  // Manual refresh: reset the failure counter and resume polling if it stopped.
  const refresh = useCallback(() => {
    failuresRef.current = 0
    setLoading(true)
    load()
    if (intervalMs > 0 && intervalRef.current === null) {
      intervalRef.current = setInterval(load, intervalMs)
    }
  }, [load, intervalMs])

  useEffect(() => {
    failuresRef.current = 0
    setLoading(true)
    load()
    if (intervalMs > 0) {
      intervalRef.current = setInterval(load, intervalMs)
      return stopPolling
    }
  }, [load, intervalMs, path, stopPolling])

  return { data, error, loading, refresh }
}
