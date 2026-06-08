"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { usePoll } from "@/lib/usePoll"
import { cn, money } from "@/lib/utils"
import type { AccountSummary, OpenPosition } from "@/types/api"

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-2xl font-semibold">{value}</CardContent>
    </Card>
  )
}

export default function OverviewPage() {
  const account = usePoll<AccountSummary>("/api/v1/account/summary", 3000)
  const open = usePoll<OpenPosition[]>("/api/v1/positions/open", 3000)
  const a = account.data
  const unit = a?.currency_unit ?? "USD"
  const positions = open.data ?? []
  const openPnl = positions.reduce((s, p) => s + p.current_pnl_usd, 0)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Overview</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {a ? (
          <>
            <Stat title="Balance" value={money(a.balance, unit)} />
            <Stat title="Equity" value={money(a.equity, unit)} />
            <Stat title="Open positions" value={String(a.open_count)} />
            <Stat title="Exposure (risk)" value={money(a.total_exposure, unit)} />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
        )}
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>
            Open positions · unrealized{" "}
            <span className={cn(openPnl < 0 ? "text-destructive" : "text-[hsl(var(--success))]")}>
              {money(openPnl, unit)}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {open.loading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-8" />
              <Skeleton className="h-8" />
            </div>
          ) : positions.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No open positions.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="p-3 font-medium">Symbol</th>
                  <th className="p-3 font-medium">Type</th>
                  <th className="p-3 font-medium">Entry</th>
                  <th className="p-3 font-medium">Current</th>
                  <th className="p-3 font-medium">Conf</th>
                  <th className="p-3 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.position_id} className="border-b last:border-0">
                    <td className="p-3 font-medium">{p.symbol}</td>
                    <td className="p-3">{p.position_type}</td>
                    <td className="p-3 tabular-nums">{p.entry_price}</td>
                    <td className="p-3 tabular-nums">{p.current_price ?? "—"}</td>
                    <td className="p-3 tabular-nums">{p.confluence_score.toFixed(0)}</td>
                    <td
                      className={cn(
                        "p-3 text-right tabular-nums",
                        p.current_pnl_usd < 0
                          ? "text-destructive"
                          : "text-[hsl(var(--success))]",
                      )}
                    >
                      {money(p.current_pnl_usd, unit)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
