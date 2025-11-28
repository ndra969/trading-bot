# 🏗️ Dashboard Technical Architecture

## Overview

This document provides detailed technical architecture of the **Trading Bot Web Dashboard**, built with Next.js 14, Tailwind CSS v4, TypeScript, and shadcn/ui components.

**Status**: MVP Frontend Implementation Complete (Phase 6.0)
**Last Updated**: October 27, 2025

---

## Technology Stack

### Core Technologies
- **Next.js 14.2.24** - React framework with App Router
- **TypeScript 5** - Type-safe development
- **Tailwind CSS v4** - Utility-first CSS framework (latest alpha)
- **shadcn/ui** - Accessible component library
- **React 19** - Latest React with RSC support
- **Lucide React** - Icon library

### Frontend Architecture
- **App Router** - File-based routing with Server Components
- **Client Components** - Interactive components with 'use client'
- **Mock Data** - Development data without backend integration
- **Responsive Design** - Mobile-first responsive layout

---

## Project Structure

```
dashboard/
├── app/
│   ├── layout.tsx              # Root layout with dark mode
│   ├── page.tsx                # Homepage dashboard
│   ├── globals.css             # Global dark theme styles
│   ├── positions/
│   │   └── page.tsx            # Positions management page
│   ├── portfolio/              # [Planned] Portfolio page
│   ├── analytics/              # [Planned] Analytics page
│   ├── signals/                # [Planned] Signals page
│   ├── activity/               # [Planned] Activity page
│   └── settings/               # [Planned] Settings page
├── components/
│   ├── layout/
│   │   ├── dashboard-layout.tsx  # Main dashboard layout wrapper
│   │   ├── header.tsx            # Top navigation header
│   │   └── sidebar.tsx           # Left navigation sidebar
│   ├── positions/
│   │   ├── positions-table.tsx         # Positions data table
│   │   └── position-details-modal.tsx  # Position details dialog
│   └── ui/                      # shadcn/ui components
│       ├── card.tsx             # Card component
│       ├── badge.tsx            # Badge component
│       ├── button.tsx           # Button component
│       ├── dialog.tsx           # Dialog/Modal component
│       ├── separator.tsx        # Separator component
│       ├── table.tsx            # Table component
│       └── dropdown-menu.tsx    # Dropdown menu component
├── lib/
│   ├── mock-data.ts            # Mock trading data
│   └── utils.ts                # Utility functions
├── types/
│   └── trading.ts              # TypeScript type definitions
├── public/                     # Static assets
├── tailwind.config.ts          # Tailwind v4 configuration
├── next.config.ts              # Next.js configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Dependencies

```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js App Router                       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   app/       │  │ components/  │  │    lib/      │      │
│  │   layout.tsx │  │   layout/    │  │   utils.ts   │      │
│  │   page.tsx   │  │   positions/ │  │ mock-data.ts │      │
│  │   positions/ │  │   ui/        │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Tailwind CSS v4 (Dark Mode)                 │   │
│  │  - Hardcoded HSL colors for dark theme               │   │
│  │  - Gradient backgrounds                              │   │
│  │  - Trading-specific colors (profit/loss)             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Mock Data    │
                    │  (No Backend) │
                    └───────────────┘
```

---

## Detailed Component Architecture

### 1. Layout System

#### Root Layout (`app/layout.tsx`)
```typescript
// Root layout with dark mode forced
<html lang="en" className="dark" suppressHydrationWarning>
  <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
    {children}
  </body>
</html>
```

**Features**:
- Dark mode enforced via `className="dark"`
- Geist font family (Sans + Mono)
- Hydration warning suppressed for dark mode
- Metadata for SEO

#### Dashboard Layout (`components/layout/dashboard-layout.tsx`)
```typescript
// Main dashboard layout with sidebar + header
<div className="flex h-screen bg-background">
  <Sidebar open={sidebarOpen} onClose={closeSidebar} />
  <div className="flex-1 flex flex-col overflow-hidden">
    <Header onMenuClick={openSidebar} />
    <main className="flex-1 overflow-y-auto">
      {children}
    </main>
  </div>
</div>
```

**Features**:
- Responsive sidebar (mobile drawer + desktop fixed)
- Header with status indicator + user menu
- Scrollable main content area
- State management for sidebar toggle

### 2. Header Component

#### Features
- **Left**: Mobile menu button + branding
- **Center**: System status indicator + real-time clock
- **Right**: Theme toggle + notifications + user menu

#### Status Indicator
```typescript
<div className="flex items-center gap-2 px-3 py-1.5 rounded-full
               bg-gradient-to-r from-green-50 to-emerald-50
               dark:from-green-950/30 dark:to-emerald-950/30">
  <div className="w-2 h-2 bg-gradient-to-r from-green-500
                 to-emerald-500 rounded-full animate-pulse" />
  <span>System Online</span>
  <span>{currentTime.toLocaleTimeString()}</span>
</div>
```

**Real-time Clock**: Updates every second via `setInterval`

### 3. Sidebar Component

#### Navigation Items
```typescript
const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Positions', href: '/positions', icon: TrendingUp, badge: '8' },
  { name: 'Portfolio', href: '/portfolio', icon: Wallet },
  { name: 'Signals', href: '/signals', icon: Target, badge: '3' },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Activity', href: '/activity', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
]
```

**Features**:
- Active route highlighting with gradient
- Badge indicators for active items
- Smooth hover animations
- Responsive mobile overlay

### 4. Dashboard Homepage

#### Stat Cards (Top Section)
```typescript
const statCards = [
  { title: 'Total Balance', value: '$15,234.56', change: 2.5% },
  { title: 'Daily P&L', value: '$214.31', change: 2.5% },
  { title: 'Active Positions', value: '8', change: 0 },
  { title: 'Win Rate', value: '65.7%', change: 5.2% },
]
```

**Visual Features**:
- Gradient backgrounds (blue, green, purple, orange)
- Hover effects (scale + shadow + translate)
- Icon with gradient background
- Change percentage with trend indicator

#### Info Cards (Bottom Section)
Three detailed cards with gradient backgrounds:
1. **Portfolio Equity** (blue/cyan gradient)
   - Total Equity
   - Margin Used
   - Margin Available

2. **Performance** (green/emerald gradient)
   - Weekly P&L
   - Monthly P&L
   - Profit Factor

3. **Trading Stats** (purple/pink gradient)
   - Total Trades
   - Win Rate
   - Max Drawdown

**Hover Effects**: Subtle background highlight on each row

### 5. Positions Page

#### Positions Table
- **Sortable columns**: Symbol, Volume, P&L (USD), P&L (%), Pips, Open Time
- **Badge indicators**: BUY (green), SELL (orange)
- **Color-coded P&L**: Green (profit), Red (loss)
- **Actions**: Eye icon to view position details

#### Position Details Modal (Dialog)

**Visual Design**:
- Dark gradient background (gray-900 → gray-800)
- Gradient title (blue-400 → purple-400)
- Sectioned layout with gradient borders

**Sections**:
1. **P&L Summary** (3-column grid)
   - P&L (USD)
   - P&L (%)
   - P&L (Pips)

2. **Position Details** (blue/cyan gradient)
   - Volume (Lots)
   - Entry Price
   - Current Price
   - Open Time

3. **Risk Management** (purple/pink gradient)
   - Stop Loss (red)
   - Take Profit (green)
   - Commission
   - Swap

4. **Comment** (optional section)

**Interactive Features**:
- Hover effects on detail rows
- Smooth open/close animations
- Overlay backdrop

---

## Dark Theme Implementation

### Tailwind CSS v4 Dark Mode

#### Hardcoded Dark Colors (`app/globals.css`)
```css
@layer base {
  body {
    background-color: hsl(0 0% 3.9%);  /* Dark gray background */
    color: hsl(0 0% 98%);              /* Light text */
  }

  /* Force dark mode for cards */
  [data-slot="card"],
  .bg-card,
  [class*="bg-card"] {
    background-color: hsl(0 0% 7%) !important;
    color: hsl(0 0% 98%) !important;
  }

  /* Force dark mode for dialogs */
  [role="dialog"],
  .bg-background {
    background-color: hsl(0 0% 7%) !important;
    color: hsl(0 0% 98%) !important;
  }
}
```

**Why Hardcoded?**
- Tailwind v4 `bg-background` utility class issues with CSS variables
- Direct HSL values ensure consistent dark theme
- `!important` to override shadcn/ui default styles

#### Trading-Specific Colors
```css
@utility text-profit {
  color: hsl(var(--profit));  /* Green: 142 70% 50% */
}

@utility text-loss {
  color: hsl(var(--loss));    /* Red: 0 84% 60% */
}

@utility text-buy {
  color: hsl(var(--buy));     /* Green: 142 76% 45% */
}

@utility text-sell {
  color: hsl(var(--sell));    /* Orange: 38 92% 60% */
}
```

### Gradient Backgrounds

#### Pattern Used Throughout
```typescript
// Dark gradient with subtle opacity
className="bg-gradient-to-br from-blue-950/40 to-cyan-950/40"
className="bg-gradient-to-br from-green-950/40 to-emerald-950/40"
className="bg-gradient-to-br from-purple-950/40 to-pink-950/40"
className="bg-gradient-to-br from-gray-900 to-gray-800"
```

**Benefits**:
- Subtle color hints without overwhelming
- Professional trading platform aesthetic
- Better visual hierarchy
- Easy on the eyes in dark environment

---

## Type System

### Core Trading Types (`types/trading.ts`)

```typescript
export interface Position {
  id: string
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  entryPrice: number
  currentPrice: number
  stopLoss: number
  takeProfit: number
  pnl: number
  pnlPercent: number
  pnlPips: number
  commission: number
  swap: number
  openTime: string
  status: 'OPEN' | 'CLOSED'
  comment?: string
}

export interface Portfolio {
  totalBalance: number
  totalEquity: number
  marginUsed: number
  marginAvailable: number
  dailyPnL: number
  weeklyPnL: number
  monthlyPnL: number
}

export interface Stats {
  activePositions: number
  totalTrades: number
  winRate: number
  profitFactor: number
  maxDrawdown: number
}

export interface MockData {
  portfolio: Portfolio
  positions: Position[]
  stats: Stats
}
```

---

## Utility Functions

### `lib/utils.ts`

```typescript
// Currency formatting
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

// Percentage formatting
export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

// P&L color helper
export function getValueColor(value: number): string {
  if (value > 0) return 'text-profit'
  if (value < 0) return 'text-loss'
  return 'text-muted-foreground'
}

// Class name merging (from clsx + tailwind-merge)
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

---

## Mock Data Structure

### `lib/mock-data.ts`

```typescript
export const mockData: MockData = {
  portfolio: {
    totalBalance: 15234.56,
    totalEquity: 15567.12,
    marginUsed: 3456.78,
    marginAvailable: 12110.34,
    dailyPnL: 214.31,
    weeklyPnL: 892.45,
    monthlyPnL: 2547.89,
  },
  positions: [
    {
      id: 'pos_1',
      symbol: 'EURUSD',
      type: 'BUY',
      volume: 0.5,
      entryPrice: 1.0856,
      currentPrice: 1.0867,
      stopLoss: 1.0840,
      takeProfit: 1.0890,
      pnl: 55.0,
      pnlPercent: 0.36,
      pnlPips: 11.0,
      commission: 2.50,
      swap: 0.15,
      openTime: '2024-10-27T08:30:00Z',
      status: 'OPEN',
    },
    // ... 14 more positions
  ],
  stats: {
    activePositions: 8,
    totalTrades: 147,
    winRate: 65.7,
    profitFactor: 1.85,
    maxDrawdown: 8.2,
  },
}
```

---

## Responsive Design

### Breakpoints (Tailwind CSS)
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### Responsive Patterns

#### Sidebar
```typescript
// Mobile: Fixed overlay drawer
// Desktop: Fixed sidebar (always visible)
className="fixed inset-y-0 left-0 z-50 w-64
           lg:translate-x-0
           {open ? 'translate-x-0' : '-translate-x-full'}"
```

#### Grid Layouts
```typescript
// Stat cards: 1 column (mobile) → 2 (tablet) → 4 (desktop)
className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"

// Info cards: 1 column (mobile) → 2 (tablet) → 3 (desktop)
className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"

// Dialog P&L: 1 column (mobile) → 3 (desktop)
className="grid gap-4 md:grid-cols-3"
```

---

## Performance Considerations

### Current Status (MVP)
- **No optimization yet** - Focus on functionality
- **Mock data only** - No API calls
- **Client-side rendering** for interactive components
- **Server components** for static layouts

### Future Optimizations
1. **Code Splitting**
   - Dynamic imports for heavy components
   - Route-based code splitting (automatic with Next.js)

2. **Data Fetching**
   - React Query for caching
   - Incremental Static Regeneration (ISR)
   - Server-side rendering where needed

3. **Image Optimization**
   - Next.js Image component
   - Lazy loading
   - WebP format

4. **Bundle Size**
   - Tree shaking unused code
   - Bundle analyzer for monitoring
   - Dynamic imports for large dependencies

---

## Browser Compatibility

### Supported Browsers
- **Chrome/Edge**: Latest 2 versions
- **Firefox**: Latest 2 versions
- **Safari**: Latest 2 versions
- **Mobile**: iOS Safari 14+, Chrome Android

### CSS Features Used
- CSS Grid
- Flexbox
- CSS Variables
- Gradients
- Backdrop filters
- Animations (fade, slide, pulse)

---

## Accessibility

### Current Implementation
- **Semantic HTML**: Proper heading hierarchy
- **ARIA labels**: Screen reader support
- **Keyboard navigation**: Tab order + focus states
- **Color contrast**: WCAG AA compliant
- **Screen reader text**: `sr-only` class for icons

### Future Improvements
- **Focus management** in modals
- **Keyboard shortcuts** for common actions
- **Skip navigation** links
- **ARIA live regions** for real-time updates

---

## Development Workflow

### Package Manager
```bash
npm run dev         # Start development server (port 3000)
npm run build       # Production build
npm run start       # Start production server
npm run lint        # ESLint
```

### Dependencies
```json
{
  "dependencies": {
    "next": "14.2.24",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tailwindcss": "^4.0.0-alpha.37",
    "lucide-react": "^0.468.0",
    "@radix-ui/react-*": "latest"
  }
}
```

---

## Known Issues & Solutions

### Issue 1: Tailwind v4 CSS Variables
**Problem**: `bg-background` utility class not applying CSS variable colors
**Solution**: Hardcoded HSL values in `@layer base` with `!important`

### Issue 2: Turbopack Cache Issues
**Problem**: Dev server panic errors during hot reload
**Solution**: Clear `.next` cache and restart server

### Issue 3: Hydration Warnings
**Problem**: Dark mode class mismatch between server/client
**Solution**: `suppressHydrationWarning` in root layout

---

## Future Enhancements

### Phase 6.1: Backend Integration
- FastAPI backend connection
- Real-time data fetching with React Query
- WebSocket for live updates
- Authentication system

### Phase 6.2: Advanced Features
- Interactive charts (Recharts/TradingView)
- Manual trading interface
- Strategy configuration
- Risk management dashboard
- Activity feed with filters

### Phase 6.3: Performance & UX
- Optimistic updates
- Loading states
- Error boundaries
- Toast notifications
- Confirmation dialogs

---

## Conclusion

This MVP implementation provides a **solid foundation** for a professional trading dashboard with:
- ✅ Modern tech stack (Next.js 14 + Tailwind v4)
- ✅ Dark theme with professional aesthetics
- ✅ Responsive layout (mobile-first)
- ✅ Type-safe development (TypeScript)
- ✅ Accessible components (shadcn/ui)
- ✅ Clean architecture (separation of concerns)

**Ready for backend integration and advanced features!**

---

**Document Version**: 1.0
**Last Updated**: October 27, 2025
**Author**: Trading Bot Team
