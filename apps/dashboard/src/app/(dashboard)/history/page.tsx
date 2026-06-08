"use client"

import { useState } from "react"

import { TimeRangePicker, useTimeRange } from "@/components/TimeRangePicker"
import { TradeDrawer } from "@/components/TradeDrawer"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { qs } from "@/lib/api"
import { usePoll } from "@/lib/usePoll"
import { cn, money } from "@/lib/utils"
import type { ClosedPosition, Page } from "@/types/api"

const LIMIT = 25

function exitVariant(t: string | null) {
  return t === "WIN" ? "success" : t === "LOSS" ? "destructive" : "muted"
}

export default function HistoryPage() {
  const { range, setRange, since } = useTimeRange("7d")
  const [offset, setOffset] = useState(0)
  const [symbol, setSymbol] = useState("")
  const [exitType, setExitType] = useState("")
  const [selected, setSelected] = useState<string | null>(null)

  const q = qs({ since, limit: LIMIT, offset, symbol, exit_type: exitType })
  const { data, loading } = usePoll<Page<ClosedPosition>>(`/api/v1/positions/closed${q}`, 15000)
  const total = data?.total ?? 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">History</h1>
        <TimeRangePicker value={range} onChange={setRange} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={symbol}
          onChange={(e) => {
            setSymbol(e.target.value.toUpperCase())
            setOffset(0)
          }}
          placeholder="Symbol filter"
          className="rounded-md border bg-card px-3 py-1.5 text-sm"
        />
        <select
          value={exitType}
          onChange={(e) => {
            setExitType(e.target.value)
            setOffset(0)
          }}
          className="rounded-md border bg-card px-3 py-1.5 text-sm"
        >
          <option value="">All outcomes</option>
          <option value="WIN">WIN</option>
          <option value="LOSS">LOSS</option>
          <option value="BREAKEVEN">BREAKEVEN</option>
        </select>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <Skeleton className="m-4 h-64" />
          ) : (data?.items.length ?? 0) === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No closed trades in range.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="p-3 font-medium">Closed</th>
                  <th className="p-3 font-medium">Symbol</th>
                  <th className="p-3 font-medium">Type</th>
                  <th className="p-3 font-medium">Outcome</th>
                  <th className="p-3 font-medium">Reason</th>
                  <th className="p-3 text-right font-medium">Conf</th>
                  <th className="p-3 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {data!.items.map((p) => (
                  <tr
                    key={p.position_id}
                    onClick={() => setSelected(p.position_id)}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="p-3 tabular-nums">
                      {p.close_time?.slice(5, 16).replace("T", " ") ?? "—"}
                    </td>
                    <td className="p-3 font-medium">{p.symbol}</td>
                    <td className="p-3">{p.position_type}</td>
                    <td className="p-3">
                      <Badge variant={exitVariant(p.exit_type)}>{p.exit_type ?? "—"}</Badge>
                    </td>
                    <td className="p-3 text-muted-foreground">{p.close_reason ?? "—"}</td>
                    <td className="p-3 text-right tabular-nums">{p.confluence_score.toFixed(0)}</td>
                    <td
                      className={cn(
                        "p-3 text-right tabular-nums",
                        p.realized_pnl_usd < 0
                          ? "text-destructive"
                          : "text-[hsl(var(--success))]",
                      )}
                    >
                      {money(p.realized_pnl_usd, p.currency_unit)}
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

      <TradeDrawer positionId={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
