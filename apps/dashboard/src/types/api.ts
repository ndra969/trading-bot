// TypeScript mirrors of trading_api.schemas (keep in sync with the Pydantic models).

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Health {
  status: string
  database: boolean
}

export interface OpenPosition {
  position_id: string
  symbol: string
  position_type: string
  status: string
  entry_price: number
  stop_loss: number
  take_profit: number
  current_price: number | null
  current_pnl_usd: number
  current_profit_pips: number
  confluence_score: number
  asset_class: string | null
  open_time: string | null
  currency_unit: string
}

export interface ClosedPosition {
  position_id: string
  symbol: string
  position_type: string
  asset_class: string | null
  exit_type: string | null
  close_reason: string | null
  is_winner: boolean | null
  realized_pnl_usd: number
  realized_profit_pips: number
  confluence_score: number
  holding_time_seconds: number
  open_time: string | null
  close_time: string | null
  currency_unit: string
}

export interface ConfluenceBreakdown {
  foundation_share: number | null
  enhancement_share: number | null
  raw_confidences: Record<string, number>
  active_layers: string[]
}

export interface PositionDetail extends ClosedPosition {
  close_price: number | null
  mae_pips: number
  mfe_pips: number
  max_profit_pips: number
  max_drawdown_pips: number
  slippage_pips: number
  entry_to_sl_pips: number
  entry_to_tp_pips: number
  breakeven_activated: boolean
  trailing_activated: boolean
  market_session: string | null
  confluence_breakdown: ConfluenceBreakdown | null
}

export interface StatRow {
  key: string
  count: number
  wins: number
  win_rate: number
  total_pnl: number
  avg_pnl: number
  avg_confluence: number
  currency_unit: string
}

export interface EquityPoint {
  close_time: string
  cumulative_pnl: number
}

export interface ConfluenceBucket {
  bucket: string
  lower: number
  upper: number
  count: number
  wins: number
  win_rate: number
  avg_pnl: number
}

export interface ConfluenceDistribution {
  asset_class: string | null
  buckets: ConfluenceBucket[]
  min: number | null
  p50: number | null
  max: number | null
}

export interface ConfluenceVsOutcome {
  buckets: ConfluenceBucket[]
  win_avg_confluence: number | null
  loss_avg_confluence: number | null
}

export interface LayerContribRow {
  layer: string
  participation_rate: number
  avg_contribution: number
}

export interface LayerContribution {
  rows: LayerContribRow[]
  coverage: number
  sample: number
}

export interface RejectionReasonRow {
  stage: string
  count: number
  avg_confluence: number | null
}

export interface RejectionSymbolRow {
  symbol: string
  stage: string
  count: number
}

export interface RejectionRecent {
  created_at: string
  symbol: string
  asset_class: string | null
  direction: string | null
  stage: string
  confluence_score: number | null
  details: Record<string, unknown>
}

export interface AccountSummary {
  broker_name: string | null
  balance: number
  equity: number
  leverage: number | null
  open_count: number
  total_exposure: number
  currency_unit: string
}

export interface SessionOut {
  session_id: string
  status: string | null
  trading_type: string | null
  start_time: string | null
  end_time: string | null
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl_usd: number
  profit_factor: number
  max_drawdown: number
  currency_unit: string
}

export interface ThresholdsOut {
  quality_thresholds: Record<string, unknown>
  confluence_weights: Record<string, unknown>
  volatility_filter: Record<string, unknown>
  commodity_gates: Record<string, unknown>
}
