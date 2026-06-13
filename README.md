# 🤖 Trading Bot - Modern Python Trading System

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1600%2B%20passing-success.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-98%25-success.svg)](htmlcov/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A sophisticated, **production-ready** automated trading bot for multi-asset trading
(Forex, Commodities, Crypto) with MetaTrader5 — plus a read-only web dashboard for
monitoring and strategy tuning. Built as a modern **uv monorepo** with an async-first
Python core and a Next.js frontend.

## 🌟 Current Status

- ✅ **Core Architecture** — async-first engine, config system, SQLAlchemy 2.0
- ✅ **Foundation Strategy** — Supply & Demand + 7 confluence layers
- ✅ **Position & Risk** — live breakeven / trailing / partial close, layered risk
- ✅ **Monitoring** — Telegram notifications + heartbeat
- ✅ **Dashboard & API** — read-only FastAPI BFF + Next.js UI (monitoring + tuning)
- 🧪 **1600+ tests passing**, 98% coverage

## 🏗️ Architecture (Monorepo)

A single [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/). The
root `pyproject.toml` is a virtual workspace root; each package ships its own
`pyproject.toml`.

```
trading-bot/
├── packages/
│   ├── core/        # trading_core — shared: config, data (models/db/repos),
│   │                #   enums, utils. Depends on nothing internal.
│   ├── worker/      # trading_worker — the bot engine (CLI: `trading-bot`)
│   │                #   connectors/ executors/ position/ risk/ strategies/ services/
│   └── api/         # trading_api — read-only FastAPI BFF (dashboard backend)
├── apps/
│   └── dashboard/   # Next.js 16 + React 19 + Tailwind frontend
├── tests/           # 1600+ tests (unit / integration / api / utils)
├── config/          # YAML configs (loaded relative to repo root)
├── docs/            # User & architecture docs
├── specs/           # 3-file specs (requirements / design / tasks)
└── alembic/         # DB migrations
```

> Dependency rule: `trading_core` depends on nothing internal;
> `trading_worker` and `trading_api` depend **only** on `trading_core`, never on
> each other. The dashboard shares only the database with the bot — it never imports
> bot code and cannot place trades.

## ✨ Features

### 🧠 Foundation-First Strategy
- **Supply & Demand** foundation (30% weight) + 7 confluence layers
- Weighted scoring — **min 65% confluence** required to signal
- Layers: `trendline 0.20 · price_action 0.15 · fibonacci 0.12 · breakout 0.12 ·
  rsi 0.10 · structure 0.08 · ma 0.08`
- Multi-timeframe analysis, fully YAML-configurable

### 🛡️ Layered Risk Management
- Max **2%** portfolio risk per trade, **1%** daily loss limit
- Emergency stop at **15%** drawdown
- Position → portfolio → account layered checks
- Asset-class & symbol-specific exposure limits

### 💼 Advanced Position Management
- Real-time pip & USD P&L tracking
- 🔄 **Breakeven** · 📉 **Trailing stop** · ✂️ **Size-aware partial close**
- Asset-specific logic (forex 15p · gold 500p · crypto $50)
- **Max 1 trade per symbol** across all strategies

### 📡 Monitoring
- **Telegram** alerts (trades / errors / status) with async non-blocking queue
- Heartbeat health checks (balance & status)
- **Web dashboard** — positions, history, analytics, rejections, live config tuning

### 🏗️ Core Stack
- **uv** workspace · **Click + Rich** CLI · **SQLAlchemy 2.0** (async)
- **Pydantic** config · **Loguru** logging · **MetaTrader5** integration
- Async-first throughout · TDD · Black / Ruff / mypy clean

## 📦 Installation

```bash
# Install all workspace packages + dependencies
uv sync

# With development tools
uv sync --extra dev

# With all optional dependencies
uv sync --all-extras
```

## 🚀 Quick Start — Bot

### 1. Setup environment

```bash
# Development environment file (.env.dev)
cat > .env.dev << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
LOG_LEVEL=DEBUG
DRY_RUN=true
EOF
```

### 2. Run the bot

```bash
# SAFE mode — mock MT5, simulated data, works offline, zero risk ✅
uv run trading-bot start --dry-run

# Real MT5 data, but simulated orders — zero risk ✅
uv run trading-bot start --dry-run --connect-mt5

# LIVE mode — real MT5, REAL ORDERS, ⚠️ REAL MONEY AT RISK
uv run trading-bot start

# Status & config
uv run trading-bot status
uv run trading-bot config validate
```

### 3. Common commands

```bash
# Bot control
uv run trading-bot start [--dry-run] [--connect-mt5]
uv run trading-bot stop
uv run trading-bot status
uv run trading-bot version

# Configuration
uv run trading-bot config validate
uv run trading-bot config show

# MT5 & account
uv run trading-bot mt5 connect | disconnect | status
uv run trading-bot account info
```

## 📊 Quick Start — Dashboard & API

A read-only web UI for monitoring and strategy tuning. It runs **independently** of
the bot and shares only the database.

```
Browser → Next.js proxy (/api/proxy/*) → FastAPI BFF (:8000) → Postgres
```

```bash
# Terminal 1 — API (FastAPI BFF) → http://localhost:8000/docs
uv run uvicorn trading_api.app:app --port 8000

# Terminal 2 — dashboard (Next.js) → http://localhost:3000
cd apps/dashboard
npm install
npm run dev
```

**Dashboard pages:** Overview · Positions · History · Analytics · Rejections · Tuning
**API routers:** `account` · `positions` · `analytics` · `rejections` · `sessions` · `config`

> Full guide: [docs/guides/dashboard-guide.md](docs/guides/dashboard-guide.md)

## 🧪 Testing

```bash
# Full suite with coverage (bot)
uv run pytest tests/ \
  --cov=packages/core/src/trading_core \
  --cov=packages/worker/src/trading_worker \
  --cov-fail-under=85

# API tests only
uv run pytest tests/api/

# Specific file / directory
uv run pytest tests/unit/test_config.py -v
uv run pytest tests/integration/ -v
```

Coverage targets: **85%** min · **95%** critical · **100%** new features.
Test types: unit · integration · api · property (Hypothesis).

## 🔧 Development

```bash
# Format · lint · type-check (the three quality gates)
uv run black packages/ tests/
uv run ruff check packages/ tests/ --fix
uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker

# All at once
uv run black packages/ tests/ && \
  uv run ruff check packages/ tests/ --fix && \
  uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker
```

**Pre-commit:** `/test && /quality fix && /dry-run` (see `CLAUDE.md` for Claude Code
slash commands and the full developer workflow).

## 🗄️ Database

- **Dev:** SQLite (`aiosqlite`) · **Prod:** PostgreSQL (`asyncpg`)
- Migrations via **Alembic** (`uv run alembic upgrade head`)

## 🔑 Environment Variables

Config priority: **ENV → env YAML → specific YAML → default YAML → code defaults**

**Development (`.env.dev`):**
```bash
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ENABLED=true
TRADING_RISK_PER_TRADE=0.001   # 0.1%
TRADING_MAX_POSITIONS=3
LOG_LEVEL=DEBUG
DRY_RUN=true                    # No real trades
```

**Production (`.env.prd`):**
```bash
# ⚠️ WARNING: LIVE TRADING with REAL MONEY
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/trading_bot_prd
MT5_LOGIN=your_real_login
MT5_PASSWORD=your_real_password
MT5_SERVER=YourBroker-Real
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ENABLED=true
TRADING_RISK_PER_TRADE=0.005   # 0.5%
TRADING_MAX_POSITIONS=5
EMERGENCY_STOP_ENABLED=true
DAILY_LOSS_LIMIT_PERCENT=5.0
DRY_RUN=false                   # ⚠️ LIVE TRADING ENABLED
```

```bash
# Development (loads .env.dev automatically)
uv run trading-bot --config development start

# Production (loads .env.prd automatically)
uv run trading-bot --config production start
```

## 📖 Documentation

- [docs/README.md](docs/README.md) — documentation index (start here)
- [docs/architecture/architecture-guide.md](docs/architecture/architecture-guide.md) — architecture
- [docs/architecture/database-erd.md](docs/architecture/database-erd.md) — database ERD
- [docs/guides/coding-standards.md](docs/guides/coding-standards.md) — coding standards ⚠️ read first
- [docs/guides/dashboard-guide.md](docs/guides/dashboard-guide.md) — dashboard guide
- [docs/guides/troubleshooting-guide.md](docs/guides/troubleshooting-guide.md) — troubleshooting
- [CLAUDE.md](CLAUDE.md) — AI assistant guidance & slash commands

## ⚠️ Requirements

- **Windows 10/11** (required for MT5 integration)
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 18+** (for the dashboard)
- **MetaTrader5** terminal installed and logged in

## 🔧 Troubleshooting

### Log File Locked (`WinError 32`)
Happens with multiple bot instances or an unclean shutdown.

```powershell
# Kill trading bot processes (interactive script)
uv run python scripts/kill_trading_bot.py

# Or, nuclear option (⚠️ kills ALL Python processes)
Get-Process python* | Stop-Process -Force
```
**Prevention:** always stop with `Ctrl+C` and wait for graceful shutdown.

### MT5 "not connected" while terminal is running
1. Confirm the MT5 terminal is logged into the correct account.
2. Verify credentials: `uv run trading-bot config show`.
3. Ensure `mt5.server` in `config/development.yaml` matches your broker's server.

### MT5 auto-switching servers
Set `server` explicitly in `config/development.yaml` (never leave it commented):
```yaml
mt5:
  login: 159394302
  server: "Exness-MT5Real20"   # CRITICAL: force the specific server
  timeout: 60000
```
The bot monitors server changes every loop and stops + alerts on a mismatch to
prevent trading on the wrong server.

More: [docs/guides/troubleshooting-guide.md](docs/guides/troubleshooting-guide.md)

## 🤝 Contributing

TDD methodology — all contributions should:
- Include comprehensive tests (maintain 85%+ coverage)
- Pass Black formatting, Ruff linting, and mypy type checking

## 📝 License

MIT License — see [LICENSE](LICENSE).

---

**Built with ❤️ using modern Python best practices**
