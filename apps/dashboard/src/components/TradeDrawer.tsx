"use client"

import { useEffect, useState } from "react"
import { X } from "lucide-react"

import { apiFetch } from "@/lib/api"
import { cn, money } from "@/lib/utils"
import type { PositionDetail } from "@/types/api"

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  )
}

/** Single-trade drill-down drawer, opened by a position_id. */
export function TradeDrawer({
  positionId,
  onClose,
}: {
  positionId: string | null
  onClose: () => void
}) {
  const [d, setD] = useState<PositionDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!positionId) return
    setD(null)
    setErr(null)
    apiFetch<PositionDetail>(`/api/v1/positions/${positionId}`)
      .then(setD)
      .catch((e) => setErr(e.message))
  }, [positionId])

  if (!positionId) return null
  const unit = d?.currency_unit ?? "USD"
  const bd = d?.confluence_breakdown

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto bg-card p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold">{d ? `${d.symbol} ${d.position_type}` : "Trade"}</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {err && <p className="text-sm text-destructive">{err}</p>}
        {!d && !err && <p className="text-sm text-muted-foreground">Loading…</p>}

        {d && (
          <div className="space-y-4">
            <section>
              <Row
                label="Outcome"
                value={
                  <span
                    className={cn(
                      d.realized_pnl_usd < 0 ? "text-destructive" : "text-[hsl(var(--success))]",
                    )}
                  >
                    {d.exit_type ?? "—"} · {money(d.realized_pnl_usd, unit)} (
                    {d.realized_profit_pips.toFixed(1)}p)
                  </span>
                }
              />
              <Row label="Close reason" value={d.close_reason ?? "—"} />
              <Row label="Confluence" value={d.confluence_score.toFixed(1)} />
              <Row label="Market session" value={d.market_session ?? "—"} />
            </section>

            <section className="border-t pt-3">
              <Row label="Entry → SL / TP" value={`${d.entry_to_sl_pips.toFixed(1)}p / ${d.entry_to_tp_pips.toFixed(1)}p`} />
              <Row label="MAE / MFE" value={`${d.mae_pips.toFixed(1)}p / ${d.mfe_pips.toFixed(1)}p`} />
              <Row label="Max profit / drawdown" value={`${d.max_profit_pips.toFixed(1)}p / ${d.max_drawdown_pips.toFixed(1)}p`} />
              <Row label="Slippage" value={`${d.slippage_pips.toFixed(1)}p`} />
              <Row label="Held" value={`${Math.round(d.holding_time_seconds / 60)} min`} />
              <Row label="Breakeven / trailing" value={`${d.breakeven_activated ? "Y" : "N"} / ${d.trailing_activated ? "Y" : "N"}`} />
            </section>

            <section className="border-t pt-3">
              <h3 className="mb-2 text-sm font-medium">Confluence breakdown</h3>
              {bd ? (
                <>
                  <Row label="Foundation" value={(bd.foundation_share ?? 0).toFixed(1)} />
                  <Row label="Enhancement" value={(bd.enhancement_share ?? 0).toFixed(1)} />
                  <div className="mt-2 space-y-1">
                    {Object.entries(bd.raw_confidences).map(([layer, conf]) => (
                      <Row key={layer} label={layer} value={conf.toFixed(1)} />
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Breakdown unavailable (trade predates breakdown persistence).
                </p>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
