"use client"

import { useState } from "react"

import { TimeRangePicker, useTimeRange } from "@/components/TimeRangePicker"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { qs } from "@/lib/api"
import { usePoll } from "@/lib/usePoll"
import { cn, money, pct } from "@/lib/utils"
import type { Page, SessionOut } from "@/types/api"

const LIMIT = 25

function statusVariant(s: string | null) {
  return s === "ACTIVE" || s === "RUNNING" ? "success" : s === "CLOSED" ? "muted" : "muted"
}

function fmt(ts: string | null) {
  return ts ? ts.slice(0, 16).replace("T", " ") : "—"
}

function duration(start: string | null, end: string | null) {
  if (!start || !end) return "—"
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms <= 0) return "—"
  const m = Math.round(ms / 60000)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m`
}

export default function SessionsPage() {
  const { range, setRange, since } = useTimeRange("30d")
  const [offset, setOffset] = useState(0)

  const q = qs({ since, limit: LIMIT, offset })
  const { data, loading } = usePoll<Page<SessionOut>>(`/api/v1/sessions${q}`, 15000)
  const total = data?.total ?? 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Sessions</h1>
        <TimeRangePicker value={range} onChange={setRange} />
      </div>
      <p className="text-sm text-muted-foreground">
        One row per bot run — each time the bot starts it opens a new trading session.
      </p>

      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <Skeleton className="m-4 h-64" />
          ) : (data?.items.length ?? 0) === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No sessions in range.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="p-3 font-medium">Started</th>
                  <th className="p-3 font-medium">Duration</th>
                  <th className="p-3 font-medium">Type</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 text-right font-medium">Trades</th>
                  <th className="p-3 text-right font-medium">Win%</th>
                  <th className="p-3 text-right font-medium">P&L</th>
                  <th className="p-3 text-right font-medium">Profit factor</th>
                  <th className="p-3 text-right font-medium">Max DD</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((s) => (
                  <tr key={s.session_id} className="border-b last:border-0">
                    <td className="p-3 tabular-nums">{fmt(s.start_time)}</td>
                    <td className="p-3 tabular-nums text-muted-foreground">
                      {duration(s.start_time, s.end_time)}
                    </td>
                    <td className="p-3 text-muted-foreground">{s.trading_type ?? "—"}</td>
                    <td className="p-3">
                      <Badge variant={statusVariant(s.status)}>{s.status ?? "—"}</Badge>
                    </td>
                    <td className="p-3 text-right tabular-nums">{s.total_trades}</td>
                    <td className="p-3 text-right tabular-nums">
                      {s.total_trades > 0 ? pct(s.win_rate) : "—"}
                    </td>
                    <td
                      className={cn(
                        "p-3 text-right tabular-nums",
                        s.total_pnl_usd < 0 ? "text-destructive" : "text-[hsl(var(--success))]",
                      )}
                    >
                      {money(s.total_pnl_usd, s.currency_unit)}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {s.profit_factor ? s.profit_factor.toFixed(2) : "—"}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {s.max_drawdown ? s.max_drawdown.toFixed(2) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total === 0 ? 0 : offset + 1}–{Math.min(offset + LIMIT, total)} of {total}
        </span>
        <div className="flex gap-2">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            className="rounded-md border px-3 py-1 disabled:opacity-40"
          >
            Prev
          </button>
          <button
            disabled={offset + LIMIT >= total}
            onClick={() => setOffset(offset + LIMIT)}
            className="rounded-md border px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
