# 🚀 Next.js Frontend Architecture Guide

## Overview

This document provides comprehensive guidance for implementing the Next.js 14+ frontend for the Trading Bot Dashboard with App Router, TypeScript, and Tailwind CSS.

## Project Structure & Architecture

### App Router Structure

```
src/app/
├── (auth)/                    # Authentication route group
│   ├── login/
│   │   └── page.tsx          # Login page
│   ├── register/
│   │   └── page.tsx          # Registration page
│   └── layout.tsx            # Auth layout
├── (dashboard)/              # Dashboard route group (protected)
│   ├── page.tsx              # Main dashboard overview
│   ├── positions/
│   │   ├── page.tsx          # Positions list
│   │   └── [id]/
│   │       └── page.tsx      # Position details
│   ├── portfolio/
│   │   ├── page.tsx          # Portfolio overview
│   │   └── analytics/
│   │       └── page.tsx      # Portfolio analytics
│   ├── risk/
│   │   ├── page.tsx          # Risk monitoring
│   │   └── alerts/
│   │       └── page.tsx      # Risk alerts
│   ├── trading/
│   │   ├── page.tsx          # Manual trading interface
│   │   └── orders/
│   │       └── page.tsx      # Order management
│   ├── settings/
│   │   ├── page.tsx          # General settings
│   │   ├── strategy/
│   │   │   └── page.tsx      # Strategy configuration
│   │   └── notifications/
│   │       └── page.tsx      # Notification preferences
│   └── layout.tsx           # Dashboard layout
├── api/                     # API routes (middleware)
│   └── auth/
│       └── [...nextauth]/
│           └── route.ts      # NextAuth.js API
├── globals.css              # Global styles and Tailwind
├── layout.tsx              # Root layout
└── page.tsx                # Home page (redirects to dashboard)
```

### Component Architecture

```
src/components/
├── ui/                      # Base UI components (shadcn/ui)
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   ├── table.tsx
│   ├── dialog.tsx
│   ├── dropdown.tsx
│   ├── badge.tsx
│   └── alert.tsx
├── charts/                  # Chart components
│   ├── LineChart.tsx         # Generic line chart
│   ├── AreaChart.tsx         # Area chart for P&L
│   ├── PieChart.tsx          # Asset allocation
│   ├── BarChart.tsx          # Volume/bar charts
│   ├── CandlestickChart.tsx   # Price charts
│   └── HeatmapChart.tsx      # Correlation heatmap
├── layout/                  # Layout components
│   ├── Header.tsx            # Top navigation
│   ├── Sidebar.tsx          # Sidebar navigation
│   ├── Footer.tsx            # Footer
│   ├── Navigation.tsx        # Navigation logic
│   └── MobileNav.tsx        # Mobile navigation
├── forms/                   # Form components
│   ├── LoginForm.tsx         # Login form
│   ├── PositionForm.tsx      # Position entry
│   ├── StrategyForm.tsx      # Strategy config
│   └── SettingsForm.tsx      # Settings forms
├── tables/                  # Table components
│   ├── PositionsTable.tsx    # Active positions
│   ├── TradeHistoryTable.tsx # Trade history
│   ├── OrdersTable.tsx       # Pending orders
│   └── AlertsTable.tsx       # Risk alerts
├── widgets/                 # Dashboard widgets
│   ├── BalanceWidget.tsx     # Account balance
│   ├── PnLWidget.tsx        # Profit/Loss
│   ├── RiskWidget.tsx        # Risk metrics
│   ├── PositionsWidget.tsx    # Position count
│   └── ActivityWidget.tsx    # Recent activity
└── providers/               # Context providers
    ├── QueryProvider.tsx     # React Query
    ├── ThemeProvider.tsx     # Theme context
    └── AuthProvider.tsx      # Authentication
```

## Technology Stack Details

### Core Dependencies

```json
{
  "dependencies": {
    "next": "14.0.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.2.2",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.6",
    "react-hook-form": "^7.47.0",
    "@hookform/resolvers": "^3.3.2",
    "zod": "^3.22.4",
    "recharts": "^2.8.0",
    "lucide-react": "^0.288.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^1.14.0",
    "class-variance-authority": "^0.7.0",
    "axios": "^1.5.0",
    "date-fns": "^2.30.0",
    "next-auth": "^4.24.0"
  },
  "devDependencies": {
    "@types/node": "^20.8.0",
    "eslint": "^8.51.0",
    "eslint-config-next": "14.0.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^6.1.0",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0"
  }
}
```

### Tailwind CSS Configuration

#### `tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Trading specific colors
        profit: '#22c55e',     // Green for profits
        loss: '#ef4444',        // Red for losses
        neutral: '#6b7280',      // Gray for neutral
        buy: '#10b981',         // Green for buy signals
        sell: '#f59e0b',        // Orange for sell signals
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'chart-grow': 'chartGrow 1s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        chartGrow: {
          '0%': { transform: 'scaleY(0)', transformOrigin: 'bottom' },
          '100%': { transform: 'scaleY(1)', transformOrigin: 'bottom' },
        },
      },
      // Custom spacing for trading layout
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
};
```

## Core Implementation Patterns

### 1. Authentication & Authorization

#### Auth Provider with Zustand
```typescript
// src/store/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'trader' | 'viewer';
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (credentials) => {
        try {
          const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials),
          });

          if (!response.ok) throw new Error('Login failed');

          const { user, token } = await response.json();

          set({ user, token, isAuthenticated: true });
        } catch (error) {
          console.error('Login error:', error);
          throw error;
        }
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      refreshToken: async () => {
        const { token } = get();
        if (!token) return;

        try {
          const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          });

          if (!response.ok) throw new Error('Token refresh failed');

          const { token: newToken } = await response.json();
          set({ token: newToken });
        } catch (error) {
          console.error('Token refresh error:', error);
          get().logout();
        }
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
```

#### Route Protection Middleware
```typescript
// src/components/ProtectedRoute.tsx
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'trader' | 'viewer';
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole
}) => {
  const { isAuthenticated, user } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
      return;
    }

    if (requiredRole && user && !hasRequiredRole(user.role, requiredRole)) {
      router.push('/unauthorized');
      return;
    }
  }, [isAuthenticated, user, requiredRole, router]);

  if (!isAuthenticated || (requiredRole && !hasRequiredRole(user?.role, requiredRole))) {
    return <div>Loading...</div>;
  }

  return <>{children}</div>;
};

function hasRequiredRole(userRole: string, requiredRole: string): boolean {
  const roleHierarchy = ['viewer', 'trader', 'admin'];
  const userLevel = roleHierarchy.indexOf(userRole);
  const requiredLevel = roleHierarchy.indexOf(requiredRole);
  return userLevel >= requiredLevel;
}
```

### 2. Data Fetching with React Query

#### API Client Configuration
```typescript
// src/lib/api-client.ts
import axios, { AxiosInstance } from 'axios';
import { useAuthStore } from '@/store/authStore';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 10000,
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const { token } = useAuthStore.getState();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await useAuthStore.getState().refreshToken();
            const { token } = useAuthStore.getState();

            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            useAuthStore.getState().logout();
            window.location.href = '/auth/login';
          }
        }

        return Promise.reject(error);
      }
    );
  }

  get<T>(url: string, params?: any) {
    return this.client.get<T>(url, { params });
  }

  post<T>(url: string, data?: any) {
    return this.client.post<T>(url, data);
  }

  put<T>(url: string, data?: any) {
    return this.client.put<T>(url, data);
  }

  delete<T>(url: string) {
    return this.client.delete<T>(url);
  }
}

export const apiClient = new ApiClient();
```

#### Custom Hooks for Data Fetching
```typescript
// src/hooks/usePositions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Position } from '@/types/trading';

export const usePositions = () => {
  return useQuery({
    queryKey: ['positions'],
    queryFn: async () => {
      const { data } = await apiClient.get<Position[]>('/api/positions');
      return data;
    },
    refetchInterval: 5000, // Real-time updates every 5 seconds
    staleTime: 1000,
  });
};

export const useClosePosition = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (positionId: string) => {
      const { data } = await apiClient.post(`/api/positions/${positionId}/close`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
};

export const useModifyPosition = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      positionId,
      stopLoss,
      takeProfit
    }: {
      positionId: string;
      stopLoss?: number;
      takeProfit?: number;
    }) => {
      const { data } = await apiClient.put(`/api/positions/${positionId}`, {
        stop_loss: stopLoss,
        take_profit: takeProfit,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
    },
  });
};
```

### 3. State Management with Zustand

#### Global Store Structure
```typescript
// src/store/index.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Trading store
interface TradingState {
  selectedSymbol: string;
  selectedTimeframe: string;
  tradingType: 'scalping' | 'day_trading' | 'swing_trading' | 'position_trading';
  autoRefresh: boolean;
  refreshInterval: number;
  actions: {
    setSelectedSymbol: (symbol: string) => void;
    setSelectedTimeframe: (timeframe: string) => void;
    setTradingType: (type: TradingState['tradingType']) => void;
    toggleAutoRefresh: () => void;
    setRefreshInterval: (interval: number) => void;
  };
}

export const useTradingStore = create<TradingState>()(
  devtools(
    (set, get) => ({
      selectedSymbol: 'EURUSD',
      selectedTimeframe: 'H1',
      tradingType: 'day_trading',
      autoRefresh: true,
      refreshInterval: 5000,

      actions: {
        setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
        setSelectedTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
        setTradingType: (type) => set({ tradingType: type }),
        toggleAutoRefresh: () => set((state) => ({ autoRefresh: !state.autoRefresh })),
        setRefreshInterval: (interval) => set({ refreshInterval: interval }),
      },
    }),
    {
      name: 'trading-store',
    }
  )
);

// UI store for theme, sidebar state, etc.
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  notifications: Notification[];
  actions: {
    toggleSidebar: () => void;
    setTheme: (theme: UIState['theme']) => void;
    addNotification: (notification: Notification) => void;
    removeNotification: (id: string) => void;
  };
}

export const useUIStore = create<UIState>()(
  devtools(
    (set, get) => ({
      sidebarOpen: true,
      theme: 'system',
      notifications: [],

      actions: {
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setTheme: (theme) => set({ theme }),
        addNotification: (notification) =>
          set((state) => ({
            notifications: [...state.notifications, { ...notification, id: Date.now().toString() }]
          })),
        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter(n => n.id !== id)
          })),
      },
    }),
    {
      name: 'ui-store',
    }
  )
);
```

### 4. Chart Components with Recharts

#### Generic Chart Component
```typescript
// src/components/charts/BaseChart.tsx
import {
  ResponsiveContainer,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { cn } from '@/lib/utils';

interface BaseChartProps {
  children: React.ReactNode;
  data: any[];
  width?: number | string;
  height?: number;
  margin?: any;
  className?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
  showLegend?: boolean;
}

export const BaseChart: React.FC<BaseChartProps> = ({
  children,
  data,
  width = '100%',
  height = 400,
  margin = { top: 5, right: 30, left: 20, bottom: 5 },
  className,
  showGrid = true,
  showTooltip = true,
  showLegend = false,
}) => {
  return (
    <div className={cn('w-full', className)}>
      <ResponsiveContainer width={width} height={height}>
        {React.Children.map(children, (child) => {
          return React.cloneElement(child, {
            data,
            margin,
          });
        })}
      </ResponsiveContainer>
    </div>
  );
};
```

#### Candlestick Chart for Price Data
```typescript
// src/components/charts/CandlestickChart.tsx
import { ComposedChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { BaseChart } from './BaseChart';
import { format } from 'date-fns';

interface CandlestickData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data: CandlestickData[];
  height?: number;
  showVolume?: boolean;
  colorUp?: string;
  colorDown?: string;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  height = 400,
  showVolume = true,
  colorUp = '#22c55e',
  colorDown = '#ef4444',
}) => {
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="text-sm font-semibold">
            {format(new Date(data.timestamp), 'MMM dd, yyyy HH:mm')}
          </p>
          <p className="text-sm">Open: <span className="font-mono">{data.open.toFixed(5)}</span></p>
          <p className="text-sm">High: <span className="font-mono">{data.high.toFixed(5)}</span></p>
          <p className="text-sm">Low: <span className="font-mono">{data.low.toFixed(5)}</span></p>
          <p className="text-sm">Close: <span className="font-mono">{data.close.toFixed(5)}</span></p>
          {showVolume && (
            <p className="text-sm">Volume: <span className="font-mono">{data.volume.toLocaleString()}</span></p>
          )}
        </div>
      );
    }
    return null;
  };

  // Transform data for candlestick representation
  const chartData = data.map(item => ({
    ...item,
    candleColor: item.close >= item.open ? colorUp : colorDown,
  }));

  return (
    <BaseChart data={chartData} height={height} showTooltip={false}>
      <ComposedChart>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value) => format(new Date(value), 'HH:mm')}
          className="text-xs"
        />
        <YAxis
          domain={['dataMin - 0.0001', 'dataMax + 0.0001']}
          className="text-xs"
          tickFormatter={(value) => value.toFixed(4)}
        />

        {showVolume && (
          <Area
            type="monotone"
            dataKey="volume"
            fill="#e5e7eb"
            stroke="#9ca3af"
            opacity={0.3}
            yAxisId="volume"
          />
        )}

        <Tooltip content={<CustomTooltip />} />
      </ComposedChart>
    </BaseChart>
  );
};
```

### 5. Form Handling with React Hook Form

#### Strategy Configuration Form
```typescript
// src/components/forms/StrategyForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';

const strategySchema = z.object({
  tradingType: z.enum(['scalping', 'day_trading', 'swing_trading', 'position_trading']),
  riskPerTrade: z.number().min(0.1).max(5.0),
  maxPositions: z.number().min(1).max(10),
  stopLossPips: z.number().min(5).max(500),
  takeProfitPips: z.number().min(10).max(1000),
  enableTrailing: z.boolean(),
  trailingDistance: z.number().min(5).max(200),
});

type StrategyFormData = z.infer<typeof strategySchema>;

interface StrategyFormProps {
  initialValues?: Partial<StrategyFormData>;
  onSubmit: (data: StrategyFormData) => Promise<void>;
  loading?: boolean;
}

export const StrategyForm: React.FC<StrategyFormProps> = ({
  initialValues,
  onSubmit,
  loading = false,
}) => {
  const form = useForm<StrategyFormData>({
    resolver: zodResolver(strategySchema),
    defaultValues: {
      tradingType: 'day_trading',
      riskPerTrade: 1.0,
      maxPositions: 5,
      stopLossPips: 50,
      takeProfitPips: 100,
      enableTrailing: false,
      trailingDistance: 25,
      ...initialValues,
    },
  });

  const handleSubmit = async (data: StrategyFormData) => {
    try {
      await onSubmit(data);
      form.reset();
    } catch (error) {
      console.error('Strategy form submission error:', error);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Strategy Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="tradingType"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Trading Type</FormLabel>
                  <FormControl>
                    <Select {...field}>
                      <option value="scalping">Scalping (1-240 min)</option>
                      <option value="day_trading">Day Trading (30-1440 min)</option>
                      <option value="swing_trading">Swing Trading (1-7 days)</option>
                      <option value="position_trading">Position Trading (1-4 weeks)</option>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="riskPerTrade"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Risk per Trade (%)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="5.0"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="maxPositions"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Max Positions</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        max="10"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="stopLossPips"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Stop Loss (pips)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="5"
                        max="500"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="takeProfitPips"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Take Profit (pips)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="10"
                        max="1000"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value))}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Saving...' : 'Save Configuration'}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
};
```

## Performance Optimizations

### 1. Code Splitting & Lazy Loading

```typescript
// Dynamic imports for heavy components
const CandlestickChart = dynamic(() => import('@/components/charts/CandlestickChart'), {
  loading: () => <div className="h-96 bg-gray-100 animate-pulse rounded-lg" />,
  ssr: false,
});

const PositionDetails = dynamic(() => import('@/components/PositionDetails'), {
  loading: () => <div className="p-4 bg-white rounded-lg shadow">Loading...</div>,
});
```

### 2. Image & Asset Optimization

```typescript
// next.config.js
module.exports = {
  images: {
    domains: ['localhost'],
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  experimental: {
    optimizePackageImports: ['recharts', 'lucide-react'],
  },
};
```

### 3. Bundle Size Analysis

```bash
# Analyze bundle size
npm run build
npm run analyze

# Output shows:
# Page                    Size     First Load JS
# ┌ ○ /                    749 B          81.4 kB
# ├ ○ /auth/login           2.2 kB        84.4 kB
# ├ λ /dashboard            8.1 kB        104 kB
# └ λ /api/positions       0 B            81.4 kB
```

## Testing Strategy

### 1. Component Testing with React Testing Library

```typescript
// __tests__/components/PositionTable.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PositionTable } from '@/components/tables/PositionsTable';

const mockPositions = [
  {
    id: '1',
    symbol: 'EURUSD',
    type: 'BUY',
    volume: 0.1,
    entryPrice: 1.0850,
    currentPrice: 1.0860,
    profit: 10,
    profitPips: 10,
    openTime: '2024-01-15T10:30:00Z',
    status: 'OPEN',
  },
];

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const renderWithClient = (component: React.ReactElement) => {
  const client = createTestQueryClient();
  return render(
    <QueryClientProvider client={client}>
      {component}
    </QueryClientProvider>
  );
};

describe('PositionTable', () => {
  it('displays positions correctly', () => {
    renderWithClient(<PositionTable positions={mockPositions} />);

    expect(screen.getByText('EURUSD')).toBeInTheDocument();
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText('0.1')).toBeInTheDocument();
    expect(screen.getByText('+10.0')).toBeInTheDocument();
  });

  it('handles position close action', async () => {
    const onClosePosition = jest.fn();
    renderWithClient(
      <PositionTable
        positions={mockPositions}
        onClosePosition={onClosePosition}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    closeButton.click();

    await waitFor(() => {
      expect(onClosePosition).toHaveBeenCalledWith('1');
    });
  });
});
```

### 2. Integration Testing

```typescript
// __tests__/integration/dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DashboardPage } from '@/app/(dashboard)/page';

// Mock API responses
jest.mock('@/hooks/usePositions', () => ({
  usePositions: () => ({
    data: mockPositions,
    isLoading: false,
    error: null,
  }),
}));

jest.mock('@/hooks/usePortfolio', () => ({
  usePortfolio: () => ({
    data: mockPortfolio,
    isLoading: false,
    error: null,
  }),
}));

describe('Dashboard Integration', () => {
  it('loads and displays all dashboard components', async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Portfolio Overview')).toBeInTheDocument();
      expect(screen.getByText('Active Positions')).toBeInTheDocument();
      expect(screen.getByText('Risk Metrics')).toBeInTheDocument();
    });

    // Verify portfolio metrics
    expect(screen.getByText('$10,000.00')).toBeInTheDocument(); // Balance
    expect(screen.getByText('3')).toBeInTheDocument(); // Active positions

    // Verify position table
    expect(screen.getByText('EURUSD')).toBeInTheDocument();
    expect(screen.getByText('GBPUSD')).toBeInTheDocument();
  });

  it('handles position interactions', async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument();
    });

    // Test position details modal
    const positionRow = screen.getByText('EURUSD').closest('tr');
    await user.click(positionRow);

    expect(screen.getByText('Position Details')).toBeInTheDocument();
    expect(screen.getByText('Close Position')).toBeInTheDocument();
  });
});
```

## Development Workflow

### 1. Local Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Start TypeScript checking in parallel
npm run type-check

# Start linting in parallel
npm run lint:watch
```

### 2. Build & Deployment

```bash
# Build for production
npm run build

# Analyze bundle size
npm run analyze

# Export static files (if needed)
npm run build && npm run export

# Run production build locally
npm run start
```

### 3. Code Quality

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Format code
npm run format

# Run all quality checks
npm run check
```

---

This architecture provides a solid foundation for building a professional, scalable trading dashboard with excellent performance and maintainability.
