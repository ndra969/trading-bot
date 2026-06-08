"use client"

import { useState } from "react"

import { TradeDrawer } from "@/components/TradeDrawer"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { usePoll } from "@/lib/usePoll"
import { cn, money } from "@/lib/utils"
import type { OpenPosition } from "@/types/api"

export default function PositionsPage() {
  const { data, loading } = usePoll<OpenPosition[]>("/api/v1/positions/open", 3000)
  const [selected, setSelected] = useState<string | null>(null)
  const rows = data ?? []

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Open positions</h1>
      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <Skeleton className="m-4 h-48" />
          ) : rows.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No open positions.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="p-3 font-medium">Symbol</th>
                  <th className="p-3 font-medium">Type</th>
                  <th className="p-3 text-right font-medium">Entry</th>
                  <th className="p-3 text-right font-medium">SL</th>
                  <th className="p-3 text-right font-medium">TP</th>
                  <th className="p-3 text-right font-medium">Current</th>
                  <th className="p-3 text-right font-medium">Conf</th>
                  <th className="p-3 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr
                    key={p.position_id}
                    onClick={() => setSelected(p.position_id)}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="p-3 font-medium">{p.symbol}</td>
                    <td className="p-3">{p.position_type}</td>
                    <td className="p-3 text-right tabular-nums">{p.entry_price}</td>
                    <td className="p-3 text-right tabular-nums">{p.stop_loss}</td>
                    <td className="p-3 text-right tabular-nums">{p.take_profit}</td>
                    <td className="p-3 text-right tabular-nums">{p.current_price ?? "—"}</td>
                    <td className="p-3 text-right tabular-nums">{p.confluence_score.toFixed(0)}</td>
                    <td
                      className={cn(
                        "p-3 text-right tabular-nums",
                        p.current_pnl_usd < 0
                          ? "text-destructive"
                          : "text-[hsl(var(--success))]",
                      )}
                    >
                      {money(p.current_pnl_usd, p.currency_unit)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
      <TradeDrawer positionId={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
