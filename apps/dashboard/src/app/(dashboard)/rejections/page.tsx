"use client"

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { TimeRangePicker, useTimeRange } from "@/components/TimeRangePicker"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { qs } from "@/lib/api"
import { usePoll } from "@/lib/usePoll"
import type { Page, RejectionReasonRow, RejectionRecent, RejectionSymbolRow } from "@/types/api"

const POLL = 60_000

export default function RejectionsPage() {
  const { range, setRange, since } = useTimeRange("7d")
  const q = qs({ since })

  const byReason = usePoll<RejectionReasonRow[]>(`/api/v1/rejections/by-reason${q}`, POLL)
  const bySymbol = usePoll<RejectionSymbolRow[]>(`/api/v1/rejections/by-symbol${q}`, POLL)
  const recent = usePoll<Page<RejectionRecent>>(
    `/api/v1/rejections/recent${qs({ since, limit: 50 })}`,
    POLL,
  )

  const chart = (byReason.data ?? []).slice(0, 10).map((r) => ({ stage: r.stage, count: r.count }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Rejections</h1>
        <TimeRangePicker value={range} onChange={setRange} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>By reason — which gate blocks the most setups</CardTitle>
        </CardHeader>
        <CardContent>
          {byReason.loading ? (
            <Skeleton className="h-72" />
          ) : chart.length === 0 ? (
            <p className="text-sm text-muted-foreground">No rejections in range.</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(220, chart.length * 32)}>
              <BarChart data={chart} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" fontSize={11} />
                <YAxis type="category" dataKey="stage" width={150} fontSize={11} />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--destructive))" />
              </BarChart>
            </ResponsiveContainer>
          )}
          {byReason.data && byReason.data.length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">
              Avg confluence at rejection shown per reason:{" "}
              {byReason.data
                .slice(0, 4)
                .map((r) => `${r.stage} ${r.avg_confluence ?? "—"}`)
                .join(" · ")}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>By symbol × reason</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {!bySymbol.data ? (
              <Skeleton className="m-4 h-40" />
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b text-left text-muted-foreground">
                  <tr>
                    <th className="p-3 font-medium">Symbol</th>
                    <th className="p-3 font-medium">Reason</th>
                    <th className="p-3 text-right font-medium">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {bySymbol.data.slice(0, 30).map((r, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3 font-medium">{r.symbol}</td>
                      <td className="p-3">{r.stage}</td>
                      <td className="p-3 text-right tabular-nums">{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent rejections</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {!recent.data ? (
              <Skeleton className="m-4 h-40" />
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b text-left text-muted-foreground">
                  <tr>
                    <th className="p-3 font-medium">Time</th>
                    <th className="p-3 font-medium">Symbol</th>
                    <th className="p-3 font-medium">Reason</th>
                    <th className="p-3 text-right font-medium">Conf</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.data.items.map((r, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3 tabular-nums">{r.created_at.slice(5, 16).replace("T", " ")}</td>
                      <td className="p-3 font-medium">{r.symbol}</td>
                      <td className="p-3">{r.stage}</td>
                      <td className="p-3 text-right tabular-nums">
                        {r.confluence_score?.toFixed(0) ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
