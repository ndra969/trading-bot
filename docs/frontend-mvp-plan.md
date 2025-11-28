# 🚀 Frontend MVP Dashboard - Implementation Plan

**Objective**: Build a professional trading dashboard UI with mock data (NO API integration yet)

**Timeline**: 3-5 days
**Approach**: Component-first, mock data, fully functional UI

---

## 🎯 Phase 1: Core Features (MVP)

### 1. Dashboard Overview Page
**Priority**: ⭐⭐⭐⭐⭐ (Highest)

**Components Needed**:
- **StatCard** - Reusable card for metrics (Balance, P&L, Win Rate, etc.)
- **PortfolioChart** - Line chart showing balance over time
- **PositionsSummaryWidget** - Quick view of active positions (top 3-5)
- **RecentActivityFeed** - Timeline of recent trades/events
- **SystemStatusWidget** - Trading bot status, connection, last sync

**Mock Data Required**:
```typescript
interface DashboardData {
  portfolio: {
    totalBalance: number;
    totalEquity: number;
    dailyPnL: number;
    weeklyPnL: number;
    monthlyPnL: number;
    marginUsed: number;
    marginAvailable: number;
  };
  stats: {
    activePositions: number;
    totalTrades: number;
    winRate: number;
    profitFactor: number;
  };
  balanceHistory: Array<{date: string; balance: number; equity: number}>;
  recentActivities: Array<{
    id: string;
    type: 'POSITION_OPENED' | 'POSITION_CLOSED' | 'SIGNAL';
    title: string;
    timestamp: string;
    severity: 'INFO' | 'SUCCESS' | 'WARNING';
  }>;
}
```

---

### 2. Positions Management Page
**Priority**: ⭐⭐⭐⭐⭐ (Highest)

**Components Needed**:
- **PositionsTable** - Full table with sorting, filtering
- **PositionDetailsModal** - Modal popup showing position details
- **PositionActions** - Buttons for Close/Modify (disabled for mock)
- **PositionFilters** - Filter by symbol, status, P&L range

**Table Columns**:
- Position ID
- Symbol
- Type (BUY/SELL) with colored badge
- Volume
- Entry Price
- Current Price
- P&L (USD & Pips) with color coding
- P&L %
- Open Time & Duration
- Stop Loss / Take Profit
- Status badge
- Actions (View Details button)

**Mock Data Required**:
```typescript
interface Position {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  volume: number;
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  pnl: number;
  pnlPips: number;
  pnlPercent: number;
  openTime: string;
  status: 'OPEN' | 'CLOSED';
  commission: number;
  swap: number;
  comment?: string;
}
```

---

### 3. Portfolio Analytics Page
**Priority**: ⭐⭐⭐⭐ (High)

**Components Needed**:
- **EquityCurveChart** - Line chart showing equity growth
- **DrawdownChart** - Area chart showing drawdown periods
- **AssetAllocationPie** - Pie chart for asset class distribution
- **PerformanceMetricsGrid** - Cards showing Sharpe ratio, win rate, etc.
- **MonthlyPerformanceHeatmap** - Calendar heatmap of monthly returns

**Mock Data Required**:
```typescript
interface PortfolioAnalytics {
  equityCurve: Array<{date: string; equity: number}>;
  drawdown: Array<{date: string; drawdown: number}>;
  assetAllocation: Array<{
    assetClass: string;
    percentage: number;
    amount: number;
    pnl: number;
  }>;
  performanceMetrics: {
    totalReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
    profitFactor: number;
    averageWin: number;
    averageLoss: number;
  };
}
```

---

### 4. Trading Signals Page (View Only)
**Priority**: ⭐⭐⭐ (Medium)

**Components Needed**:
- **SignalsTable** - List of trading signals with confidence scores
- **SignalDetailsCard** - Detailed view of signal with confluence breakdown
- **ConfluenceScoreVisual** - Radial or bar chart showing layer contributions

**Mock Data Required**:
```typescript
interface TradingSignal {
  id: string;
  symbol: string;
  signalType: 'BUY' | 'SELL' | 'HOLD';
  confidence: number; // 0-100
  foundationScore: number;
  confluenceScore: number;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  riskRewardRatio: number;
  strategyLayers: {
    foundation: number;
    trendline: number;
    priceAction: number;
    fibonacci: number;
    breakoutRetest: number;
    marketStructure: number;
  };
  timeframe: string;
  tradingType: string;
  timestamp: string;
  status: 'ACTIVE' | 'EXPIRED' | 'EXECUTED';
}
```

---

### 5. Settings Page (UI Only)
**Priority**: ⭐⭐ (Low)

**Components Needed**:
- **SettingsForm** - Form for user preferences (disabled/view only)
- **ThemeToggle** - Light/Dark mode switcher
- **NotificationSettings** - Checkboxes for notification preferences

---

## 🏗️ Project Structure

```
web-dashboard/
├── frontend/
│   ├── src/
│   │   ├── app/                          # Next.js App Router
│   │   │   ├── (dashboard)/              # Protected routes group
│   │   │   │   ├── page.tsx              # Main dashboard
│   │   │   │   ├── positions/
│   │   │   │   │   └── page.tsx          # Positions page
│   │   │   │   ├── analytics/
│   │   │   │   │   └── page.tsx          # Analytics page
│   │   │   │   ├── signals/
│   │   │   │   │   └── page.tsx          # Trading signals
│   │   │   │   ├── settings/
│   │   │   │   │   └── page.tsx          # Settings page
│   │   │   │   └── layout.tsx            # Dashboard layout
│   │   │   ├── globals.css               # Global styles + Tailwind
│   │   │   ├── layout.tsx                # Root layout
│   │   │   └── page.tsx                  # Landing page (redirect)
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                       # shadcn/ui base components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── tabs.tsx
│   │   │   │   └── select.tsx
│   │   │   │
│   │   │   ├── dashboard/                # Dashboard-specific components
│   │   │   │   ├── stat-card.tsx         # Metric cards
│   │   │   │   ├── portfolio-chart.tsx   # Balance chart
│   │   │   │   ├── positions-summary.tsx # Quick positions view
│   │   │   │   ├── activity-feed.tsx     # Recent activity
│   │   │   │   └── system-status.tsx     # Status widget
│   │   │   │
│   │   │   ├── positions/                # Positions page components
│   │   │   │   ├── positions-table.tsx   # Main table
│   │   │   │   ├── position-row.tsx      # Table row
│   │   │   │   ├── position-details.tsx  # Details modal
│   │   │   │   └── position-filters.tsx  # Filter controls
│   │   │   │
│   │   │   ├── analytics/                # Analytics components
│   │   │   │   ├── equity-curve.tsx      # Equity chart
│   │   │   │   ├── drawdown-chart.tsx    # Drawdown chart
│   │   │   │   ├── asset-allocation.tsx  # Pie chart
│   │   │   │   └── metrics-grid.tsx      # Performance metrics
│   │   │   │
│   │   │   ├── signals/                  # Signals components
│   │   │   │   ├── signals-table.tsx
│   │   │   │   ├── signal-details.tsx
│   │   │   │   └── confluence-chart.tsx
│   │   │   │
│   │   │   ├── charts/                   # Reusable charts
│   │   │   │   ├── line-chart.tsx
│   │   │   │   ├── area-chart.tsx
│   │   │   │   ├── pie-chart.tsx
│   │   │   │   └── bar-chart.tsx
│   │   │   │
│   │   │   └── layout/                   # Layout components
│   │   │       ├── header.tsx            # Top navigation
│   │   │       ├── sidebar.tsx           # Side navigation
│   │   │       ├── footer.tsx            # Footer
│   │   │       └── mobile-nav.tsx        # Mobile navigation
│   │   │
│   │   ├── lib/
│   │   │   ├── utils.ts                  # Utility functions
│   │   │   ├── mock-data.ts              # Mock data generator
│   │   │   └── formatters.ts             # Number/date formatters
│   │   │
│   │   ├── types/
│   │   │   ├── trading.ts                # Trading types
│   │   │   ├── portfolio.ts              # Portfolio types
│   │   │   └── common.ts                 # Common types
│   │   │
│   │   └── hooks/
│   │       ├── use-theme.ts              # Theme hook
│   │       ├── use-mobile.ts             # Mobile detection
│   │       └── use-mock-data.ts          # Mock data hook
│   │
│   ├── public/                           # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.js
│
└── docs/
    └── frontend-mvp-plan.md             # This file
```

---

## 🎨 Design System

### Color Palette
```css
/* Trading-specific colors */
--profit: #10b981;      /* Green for profits */
--loss: #ef4444;        /* Red for losses */
--buy: #22c55e;         /* Green for BUY signals */
--sell: #f59e0b;        /* Orange for SELL signals */
--neutral: #6b7280;     /* Gray for neutral */

/* Status colors */
--success: #22c55e;     /* Success states */
--warning: #f59e0b;     /* Warning states */
--error: #ef4444;       /* Error states */
--info: #3b82f6;        /* Info states */
```

### Typography
```css
/* Font families */
font-sans: 'Inter', sans-serif;          /* Body text */
font-mono: 'JetBrains Mono', monospace;  /* Numbers, prices */

/* Font sizes */
text-xs: 0.75rem;    /* Small labels */
text-sm: 0.875rem;   /* Table text */
text-base: 1rem;     /* Body text */
text-lg: 1.125rem;   /* Card titles */
text-xl: 1.25rem;    /* Section headers */
text-2xl: 1.5rem;    /* Metric values */
```

### Spacing & Layout
```css
/* Card spacing */
gap-4: 1rem;          /* Between cards */
gap-6: 1.5rem;        /* Between sections */
p-4: 1rem;            /* Card padding */
p-6: 1.5rem;          /* Section padding */

/* Grid layouts */
grid-cols-1 md:grid-cols-2 lg:grid-cols-4  /* Responsive stats grid */
grid-cols-1 lg:grid-cols-3                  /* Main content layout */
```

---

## 📊 Mock Data Strategy

### Data Generation Approach
1. **Static seed data** - Consistent data across refreshes
2. **Realistic values** - Based on actual trading scenarios
3. **Time-based updates** - Simulate real-time price changes (optional)

### Mock Data Files
```typescript
// lib/mock-data/portfolio.ts
export const mockPortfolioData = { /* ... */ };

// lib/mock-data/positions.ts
export const mockPositions = [ /* ... */ ];

// lib/mock-data/signals.ts
export const mockSignals = [ /* ... */ ];

// lib/mock-data/analytics.ts
export const mockAnalytics = { /* ... */ };
```

---

## 🛠️ Implementation Steps

### Day 1: Project Setup & Base Components
**Tasks**:
1. ✅ Create Next.js 14 project with TypeScript
2. ✅ Install shadcn/ui components (card, button, badge, table, dialog, tabs)
3. ✅ Setup Tailwind CSS with trading color palette
4. ✅ Install Recharts for charts
5. ✅ Install Lucide React for icons
6. ✅ Create base layout (header, sidebar, footer)
7. ✅ Create type definitions for trading data

**Deliverables**:
- Working Next.js app with navigation
- shadcn/ui components installed
- Base layout with sidebar navigation
- TypeScript types defined

---

### Day 2: Dashboard Overview Page
**Tasks**:
1. ✅ Create mock portfolio data
2. ✅ Build StatCard component (reusable)
3. ✅ Build PortfolioChart component (Recharts line chart)
4. ✅ Build PositionsSummaryWidget
5. ✅ Build RecentActivityFeed
6. ✅ Build SystemStatusWidget
7. ✅ Assemble dashboard overview page

**Deliverables**:
- Fully functional dashboard overview page
- 4-6 stat cards showing key metrics
- Line chart for balance history
- Quick positions summary
- Recent activity timeline

---

### Day 3: Positions Management Page
**Tasks**:
1. ✅ Create mock positions data (20-30 positions)
2. ✅ Build PositionsTable component with sorting
3. ✅ Build PositionRow component with color-coded P&L
4. ✅ Build PositionFilters component (symbol, status)
5. ✅ Build PositionDetailsModal component
6. ✅ Add pagination to table

**Deliverables**:
- Full positions table with sorting
- Filter controls working
- Details modal showing position info
- Responsive table for mobile

---

### Day 4: Analytics & Signals Pages
**Tasks**:
1. ✅ Create mock analytics data
2. ✅ Build EquityCurveChart (line chart)
3. ✅ Build DrawdownChart (area chart)
4. ✅ Build AssetAllocationPie (pie chart)
5. ✅ Build PerformanceMetricsGrid
6. ✅ Create mock signals data
7. ✅ Build SignalsTable component
8. ✅ Build SignalDetailsCard with confluence breakdown

**Deliverables**:
- Analytics page with 4 charts
- Performance metrics grid
- Signals page with table
- Signal details view

---

### Day 5: Polish & Responsive Design
**Tasks**:
1. ✅ Mobile responsive testing
2. ✅ Dark mode implementation
3. ✅ Loading states for all components
4. ✅ Error states (empty states)
5. ✅ Animations and transitions
6. ✅ Settings page (basic UI)
7. ✅ Documentation comments in code

**Deliverables**:
- Fully responsive across devices
- Dark mode working
- Smooth animations
- Professional polish

---

## 📱 Responsive Breakpoints

```typescript
// Mobile: 320px - 768px
<div className="grid grid-cols-1 gap-4">

// Tablet: 768px - 1024px
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">

// Desktop: 1024px+
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
```

---

## ✅ Success Criteria

### Visual Quality
- ✅ Professional appearance (no emojis, modern icons)
- ✅ Consistent spacing and alignment
- ✅ Color-coded data (green profits, red losses)
- ✅ Smooth animations and transitions

### Functionality
- ✅ All navigation links working
- ✅ Sidebar collapsible on mobile
- ✅ Tables sortable and filterable
- ✅ Modals open/close properly
- ✅ Charts render correctly

### Performance
- ✅ Page load < 2 seconds
- ✅ No console errors
- ✅ Smooth scrolling
- ✅ Fast chart rendering

### Code Quality
- ✅ TypeScript strict mode
- ✅ Component reusability
- ✅ Clean folder structure
- ✅ Inline documentation

---

## 🚫 Out of Scope (Phase 2)

**NOT included in MVP**:
- ❌ Backend API integration
- ❌ Authentication system
- ❌ Real-time WebSocket updates
- ❌ Manual trading functionality (open positions)
- ❌ Database integration
- ❌ User management
- ❌ Email/Telegram notifications
- ❌ Advanced risk management tools

**These will be added in Phase 2** after UI is complete and approved.

---

## 📦 Dependencies

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.445.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "date-fns": "^3.6.0",
    "class-variance-authority": "^0.7.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-select": "^2.1.0"
  }
}
```

---

## 🎯 Next Steps

1. **Kill the running dev server** (port 3000)
2. **Delete old web-dashboard folder** (manual jika masih locked)
3. **Create new Next.js project** with proper structure
4. **Start Day 1 implementation**

---

**Ready to start? Let me know and I'll begin with Day 1 setup!** 🚀
