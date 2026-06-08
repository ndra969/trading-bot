"use client"

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { StatTable } from "@/components/StatTable"
import { TimeRangePicker, useTimeRange } from "@/components/TimeRangePicker"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { qs } from "@/lib/api"
import { usePoll } from "@/lib/usePoll"
import type { EquityPoint, StatRow } from "@/types/api"

const POLL = 60_000

export default function AnalyticsPage() {
  const { range, setRange, since } = useTimeRange("30d")
  const q = qs({ since })

  const bySymbol = usePoll<StatRow[]>(`/api/v1/analytics/by-symbol${q}`, POLL)
  const byExit = usePoll<StatRow[]>(`/api/v1/analytics/by-exit-type${q}`, POLL)
  const equity = usePoll<EquityPoint[]>(`/api/v1/analytics/equity-curve${q}`, POLL)

  const curve = (equity.data ?? []).map((p) => ({
    t: p.close_time.slice(5, 10),
    pnl: p.cumulative_pnl,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <TimeRangePicker value={range} onChange={setRange} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Cumulative realized P&L</CardTitle>
        </CardHeader>
        <CardContent>
          {equity.loading ? (
            <Skeleton className="h-64" />
          ) : curve.length === 0 ? (
            <p className="text-sm text-muted-foreground">No closed trades in range.</p>
          ) : (
            <ResponsiveContainer width="100%" height={256}>
              <LineChart data={curve}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="t" fontSize={11} />
                <YAxis fontSize={11} width={48} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="pnl"
                  stroke="hsl(var(--primary))"
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>By symbol (worst first)</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {bySymbol.data ? (
            <StatTable rows={bySymbol.data} keyLabel="Symbol" />
          ) : (
            <Skeleton className="m-4 h-32" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>By exit type</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {byExit.data ? (
            <StatTable rows={byExit.data} keyLabel="Exit" />
          ) : (
            <Skeleton className="m-4 h-24" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
