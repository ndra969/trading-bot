"use client"

import { useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
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
import { cn } from "@/lib/utils"
import type {
  ConfluenceDistribution,
  ConfluenceVsOutcome,
  LayerContribution,
  ThresholdsOut,
} from "@/types/api"

const ASSETS = ["forex_major", "forex_jpy", "commodities", "crypto"] as const
const POLL = 60_000

const METRICS = [
  { key: "win_rate", label: "Win-rate" },
  { key: "avg_pnl", label: "Avg P&L" },
] as const
type Metric = (typeof METRICS)[number]["key"]

type BucketDatum = { bucket: string; count: number; win_rate: number; avg_pnl: number }

function BucketTooltip({ active, payload }: { active?: boolean; payload?: { payload: BucketDatum }[] }) {
  if (!active || !payload?.length) return null
  const b = payload[0].payload
  return (
    <div className="rounded-md border bg-card px-3 py-2 text-xs shadow-sm">
      <div className="font-medium">Confluence {b.bucket}</div>
      <div className="text-muted-foreground">{b.count} trades</div>
      <div className="text-muted-foreground">win-rate {b.win_rate.toFixed(1)}%</div>
      <div className={cn(b.avg_pnl < 0 ? "text-destructive" : "text-[hsl(var(--success))]")}>
        avg P&L {b.avg_pnl.toFixed(2)}
      </div>
    </div>
  )
}

export default function TuningPage() {
  const { range, setRange, since } = useTimeRange("30d")
  const [asset, setAsset] = useState<(typeof ASSETS)[number]>("forex_major")
  const [metric, setMetric] = useState<Metric>("win_rate")
  const q = qs({ since, asset_class: asset })

  const dist = usePoll<ConfluenceDistribution>(`/api/v1/analytics/confluence-distribution${q}`, POLL)
  const vo = usePoll<ConfluenceVsOutcome>(`/api/v1/analytics/confluence-vs-outcome${q}`, POLL)
  const layers = usePoll<LayerContribution>(`/api/v1/analytics/layer-contribution${q}`, POLL)
  const thresholds = usePoll<ThresholdsOut>(`/api/v1/config/thresholds`, 0)

  const qt = thresholds.data?.quality_thresholds as
    | Record<string, { min_confluence_score?: number }>
    | undefined
  const threshold = qt?.[asset]?.min_confluence_score ?? qt?.["default"]?.min_confluence_score

  const buckets = (dist.data?.buckets ?? []).map((b, i) => ({
    bucket: b.bucket,
    count: b.count,
    win_rate: vo.data?.buckets[i]?.win_rate ?? 0,
    avg_pnl: b.avg_pnl,
  }))

  // A bucket is "good" by the chosen metric: win-rate ≥ 50% or positive avg P&L.
  const isGood = (b: { win_rate: number; avg_pnl: number }) =>
    metric === "win_rate" ? b.win_rate >= 50 : b.avg_pnl > 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tuning</h1>
        <TimeRangePicker value={range} onChange={setRange} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex rounded-md border bg-card p-0.5">
          {ASSETS.map((a) => (
            <button
              key={a}
              onClick={() => setAsset(a)}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium",
                asset === a
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {a}
            </button>
          ))}
        </div>
        <div className="inline-flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Color by</span>
          <div className="inline-flex rounded-md border bg-card p-0.5">
            {METRICS.map((m) => (
              <button
                key={m.key}
                onClick={() => setMetric(m.key)}
                className={cn(
                  "rounded px-3 py-1 text-xs font-medium",
                  metric === m.key
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            Confluence distribution
            {threshold != null && (
              <span className="ml-2 font-normal text-muted-foreground">
                · threshold {threshold} (red line) · min {dist.data?.min ?? "—"} / p50{" "}
                {dist.data?.p50 ?? "—"} / max {dist.data?.max ?? "—"}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {dist.loading ? (
            <Skeleton className="h-64" />
          ) : (
            <ResponsiveContainer width="100%" height={256}>
              <BarChart data={buckets}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="bucket" fontSize={11} />
                <YAxis fontSize={11} width={40} />
                <Tooltip content={<BucketTooltip />} cursor={{ fill: "hsl(var(--muted))" }} />
                <Bar dataKey="count">
                  {buckets.map((b, i) => (
                    <Cell
                      key={i}
                      fill={isGood(b) ? "hsl(var(--success))" : "hsl(var(--primary))"}
                    />
                  ))}
                </Bar>
                {threshold != null && (
                  <ReferenceLine
                    x={`${Math.floor(threshold / 10) * 10}-${Math.floor(threshold / 10) * 10 + 10}`}
                    stroke="hsl(var(--destructive))"
                    strokeWidth={2}
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>Bar height = trades in that confluence bucket.</span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: "hsl(var(--success))" }}
              />
              {metric === "win_rate" ? "win-rate ≥ 50%" : "avg P&L > 0 (profitable)"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: "hsl(var(--primary))" }}
              />
              {metric === "win_rate" ? "win-rate < 50%" : "avg P&L ≤ 0 (losing)"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: "hsl(var(--destructive))" }}
              />
              current threshold
            </span>
          </div>
          {vo.data && (
            <p className="mt-2 text-sm text-muted-foreground">
              WIN avg confluence{" "}
              <span className="font-medium text-foreground">
                {vo.data.win_avg_confluence ?? "—"}
              </span>{" "}
              vs LOSS avg{" "}
              <span className="font-medium text-foreground">
                {vo.data.loss_avg_confluence ?? "—"}
              </span>{" "}
              — if close, confluence isn&apos;t predicting outcome.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Layer contribution
            {layers.data && (
              <span className="ml-2 font-normal text-muted-foreground">
                · coverage {(layers.data.coverage * 100).toFixed(0)}% ({layers.data.sample} trades)
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {!layers.data ? (
            <Skeleton className="m-4 h-32" />
          ) : layers.data.rows.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">
              No breakdown data yet (only trades taken after the breakdown rollout carry it).
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="p-3 font-medium">Layer</th>
                  <th className="p-3 text-right font-medium">Participation</th>
                  <th className="p-3 text-right font-medium">Avg contribution</th>
                </tr>
              </thead>
              <tbody>
                {layers.data.rows.map((r) => (
                  <tr key={r.layer} className="border-b last:border-0">
                    <td className="p-3 font-medium">{r.layer}</td>
                    <td className="p-3 text-right tabular-nums">
                      {(r.participation_rate * 100).toFixed(0)}%
                    </td>
                    <td className="p-3 text-right tabular-nums">{r.avg_contribution.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Read-only — edit values in <code>config/strategy_parameters.yaml</code>.
      </p>
    </div>
  )
}
