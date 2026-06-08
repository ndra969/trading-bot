import { cn, money, pct } from "@/lib/utils"
import type { StatRow } from "@/types/api"

export function StatTable({ rows, keyLabel }: { rows: StatRow[]; keyLabel: string }) {
  if (rows.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">No data in range.</p>
  }
  const unit = rows[0]?.currency_unit ?? "USD"
  return (
    <table className="w-full text-sm">
      <thead className="border-b text-left text-muted-foreground">
        <tr>
          <th className="p-3 font-medium">{keyLabel}</th>
          <th className="p-3 text-right font-medium">Trades</th>
          <th className="p-3 text-right font-medium">Win%</th>
          <th className="p-3 text-right font-medium">Total P&L</th>
          <th className="p-3 text-right font-medium">Avg P&L</th>
          <th className="p-3 text-right font-medium">Avg conf</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.key} className="border-b last:border-0">
            <td className="p-3 font-medium">{r.key}</td>
            <td className="p-3 text-right tabular-nums">{r.count}</td>
            <td className="p-3 text-right tabular-nums">{pct(r.win_rate)}</td>
            <td
              className={cn(
                "p-3 text-right tabular-nums",
                r.total_pnl < 0 ? "text-destructive" : "text-[hsl(var(--success))]",
              )}
            >
              {money(r.total_pnl, unit)}
            </td>
            <td className="p-3 text-right tabular-nums">{money(r.avg_pnl, unit)}</td>
            <td className="p-3 text-right tabular-nums">{r.avg_confluence.toFixed(1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
