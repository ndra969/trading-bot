# 🎨 Tailwind CSS Styling System Guide

## Overview

This document provides comprehensive guidance for implementing a Tailwind CSS styling system specifically designed for the Trading Bot Dashboard, with trading-focused color schemes, responsive design patterns, and component libraries.

## Design System Foundation

### Color Palette for Trading Interface

#### Trading-Specific Colors
```css
/* Trading Status Colors */
.profit { /* Green for profits */
  background-color: #22c55e;
  color: #22c55e;
}

.loss { /* Red for losses */
  background-color: #ef4444;
  color: #ef4444;
}

.neutral { /* Gray for neutral */
  background-color: #6b7280;
  color: #6b7280;
}

.buy-signal { /* Bright green for buy signals */
  background-color: #10b981;
  color: #10b981;
}

.sell-signal { /* Orange for sell signals */
  background-color: #f59e0b;
  color: #f59e0b;
}

/* Market Status Colors */
.market-open {
  background-color: #059669;
  color: #059669;
}

.market-closed {
  background-color: #7c3aed;
  color: #7c3aed;
}

/* Risk Level Colors */
.risk-low {
  background-color: #06b6d4;
  color: #06b6d4;
}

.risk-medium {
  background-color: #f59e0b;
  color: #f59e0b;
}

.risk-high {
  background-color: #ef4444;
  color: #ef4444;
}

.risk-critical {
  background-color: #991b1b;
  color: #991b1b;
}
```

#### Extended Color System
```javascript
// tailwind.config.js - Extended colors
theme: {
  extend: {
    colors: {
      // Base colors from shadcn/ui
      border: 'hsl(var(--border))',
      input: 'hsl(var(--input))',
      ring: 'hsl(var(--ring))',
      background: 'hsl(var(--background))',
      foreground: 'hsl(var(--foreground))',
      primary: {
        DEFAULT: 'hsl(var(--primary))',
        foreground: 'hsl(var(--primary-foreground))',
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
      },
      secondary: {
        DEFAULT: 'hsl(var(--secondary))',
        foreground: 'hsl(var(--secondary-foreground))',
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
      },

      // Trading specific colors
      profit: {
        50: '#f0fdf4',
        100: '#dcfce7',
        200: '#bbf7d0',
        300: '#86efac',
        400: '#4ade80',
        500: '#22c55e', // Main profit color
        600: '#16a34a',
        700: '#15803d',
        800: '#166534',
        900: '#14532d',
      },
      loss: {
        50: '#fef2f2',
        100: '#fee2e2',
        200: '#fecaca',
        300: '#fca5a5',
        400: '#f87171',
        500: '#ef4444', // Main loss color
        600: '#dc2626',
        700: '#b91c1c',
        800: '#991b1b',
        900: '#7f1d1d',
      },
      buy: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981', // Main buy signal color
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
      },
      sell: {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b', // Main sell signal color
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f',
      },

      // Risk level colors
      risk: {
        low: '#06b6d4',
        medium: '#f59e0b',
        high: '#ef4444',
        critical: '#991b1b',
      },

      // Chart colors for multiple series
      chart: {
        blue: '#3b82f6',
        green: '#10b981',
        red: '#ef4444',
        purple: '#8b5cf6',
        orange: '#f59e0b',
        teal: '#14b8a6',
        pink: '#ec4899',
        indigo: '#6366f1',
      },
    },
  }
}
```

### Typography System

```javascript
// Font family configuration
theme: {
  extend: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      display: ['Inter Display', 'Inter', 'sans-serif'],
    },
    fontSize: {
      'xs': ['0.75rem', { lineHeight: '1rem' }],
      'sm': ['0.875rem', { lineHeight: '1.25rem' }],
      'base': ['1rem', { lineHeight: '1.5rem' }],
      'lg': ['1.125rem', { lineHeight: '1.75rem' }],
      'xl': ['1.25rem', { lineHeight: '1.75rem' }],
      '2xl': ['1.5rem', { lineHeight: '2rem' }],
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      '5xl': ['3rem', { lineHeight: '1' }],
      '6xl': ['3.75rem', { lineHeight: '1' }],
      // Trading specific sizes
      'price-lg': ['2rem', { lineHeight: '1', fontWeight: '600' }],
      'price-xl': ['2.5rem', { lineHeight: '1', fontWeight: '700' }],
      'pips': ['0.75rem', { lineHeight: '1', fontWeight: '500' }],
    },
    fontWeight: {
      'thin': '100',
      'light': '300',
      'normal': '400',
      'medium': '500',
      'semibold': '600',
      'bold': '700',
      'extrabold': '800',
      'black': '900',
    },
  }
}
```

## Component Library

### Base UI Components

#### Button Components
```typescript
// src/components/ui/button.tsx
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',

        // Trading specific variants
        profit: 'bg-profit text-white hover:bg-profit/90',
        loss: 'bg-loss text-white hover:bg-loss/90',
        buy: 'bg-buy text-white hover:bg-buy/90',
        sell: 'bg-sell text-white hover:bg-sell/90',
        success: 'bg-green-600 text-white hover:bg-green-700',
        warning: 'bg-yellow-600 text-white hover:bg-yellow-700',
        danger: 'bg-red-600 text-white hover:bg-red-700',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
        xl: 'h-12 px-6 text-base',
        '2xl': 'h-14 px-8 text-lg',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
            {children}
          </div>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

#### Card Components
```typescript
// src/components/ui/card.tsx
import * as React from 'react';
import { cn } from '@/lib/utils';

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    variant?: 'default' | 'bordered' | 'elevated' | 'glass';
  }
>(({ className, variant = 'default', ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-lg transition-all duration-200',
      {
        'bg-card text-card-foreground': variant === 'default',
        'bg-card border border-border': variant === 'bordered',
        'bg-card shadow-lg hover:shadow-xl': variant === 'elevated',
        'bg-white/10 backdrop-blur-md border border-white/20': variant === 'glass',
      },
      className
    )}
    {...props}
  />
));
Card.displayName = 'Card';

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-2xl font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
));
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
));
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

#### Badge Components for Trading Status
```typescript
// src/components/ui/badge.tsx
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',

        // Trading specific variants
        success: 'border-transparent bg-green-500 text-white hover:bg-green-600',
        warning: 'border-transparent bg-yellow-500 text-white hover:bg-yellow-600',
        error: 'border-transparent bg-red-500 text-white hover:bg-red-600',
        info: 'border-transparent bg-blue-500 text-white hover:bg-blue-600',

        // Position status variants
        'position-buy': 'bg-buy text-white',
        'position-sell': 'bg-sell text-white',
        'position-open': 'bg-blue-500 text-white',
        'position-closed': 'bg-gray-500 text-white',

        // Risk level variants
        'risk-low': 'bg-risk-low text-white',
        'risk-medium': 'bg-risk-medium text-white',
        'risk-high': 'bg-risk-high text-white',
        'risk-critical': 'bg-risk-critical text-white',

        // P&L variants
        'pnl-positive': 'bg-profit text-white',
        'pnl-negative': 'bg-loss text-white',
        'pnl-neutral': 'bg-gray-500 text-white',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
```

### Trading-Specific Components

#### Price Display Component
```typescript
// src/components/ui/price-display.tsx
import React from 'react';
import { cn } from '@/lib/utils';

interface PriceDisplayProps {
  price: number;
  symbol?: string;
  change?: number;
  changePercent?: number;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showTrend?: boolean;
  className?: string;
}

export const PriceDisplay: React.FC<PriceDisplayProps> = ({
  price,
  symbol,
  change = 0,
  changePercent = 0,
  size = 'md',
  showTrend = true,
  className,
}) => {
  const isPositive = change >= 0;
  const trendIcon = isPositive ? '↗' : '↘';

  const sizeClasses = {
    sm: 'text-lg font-semibold',
    md: 'text-2xl font-bold',
    lg: 'text-3xl font-bold',
    xl: 'text-4xl font-bold',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-baseline gap-1">
        {symbol && <span className="text-sm text-muted-foreground">{symbol}</span>}
        <span className={cn(sizeClasses[size])}>
          {price.toFixed(5)}
        </span>
      </div>

      {showTrend && (
        <div className="flex items-center gap-1">
          <span className={cn(
            'text-sm font-medium flex items-center gap-1',
            isPositive ? 'text-profit' : 'text-loss'
          )}>
            {trendIcon}
            {Math.abs(change).toFixed(5)}
            ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
          </span>
        </div>
      )}
    </div>
  );
};
```

#### P&L Component
```typescript
// src/components/ui/pnl-display.tsx
import React from 'react';
import { cn, formatCurrency } from '@/lib/utils';

interface PnLDisplayProps {
  value: number;
  currency?: string;
  showPercentage?: boolean;
  percentage?: number;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const PnLDisplay: React.FC<PnLDisplayProps> = ({
  value,
  currency = 'USD',
  showPercentage = false,
  percentage,
  size = 'md',
  showIcon = false,
  className,
}) => {
  const isPositive = value >= 0;
  const icon = isPositive ? '+' : '';
  const trendIcon = isPositive ? '📈' : '📉';

  const sizeClasses = {
    sm: 'text-sm font-medium',
    md: 'text-lg font-semibold',
    lg: 'text-xl font-bold',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center gap-1">
        {showIcon && <span>{trendIcon}</span>}
        <span className={cn(
          sizeClasses[size],
          isPositive ? 'text-profit' : 'text-loss'
        )}>
          {icon}{formatCurrency(Math.abs(value), currency)}
        </span>
        {showPercentage && percentage !== undefined && (
          <span className={cn(
            'text-sm',
            isPositive ? 'text-profit' : 'text-loss'
          )}>
            ({isPositive ? '+' : ''}{percentage.toFixed(2)}%)
          </span>
        )}
      </div>
    </div>
  );
};
```

#### Position Status Badge
```typescript
// src/components/ui/position-badge.tsx
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { PositionStatus, PositionType } from '@/types/trading';

interface PositionBadgeProps {
  status: PositionStatus;
  type: PositionType;
  className?: string;
}

export const PositionBadge: React.FC<PositionBadgeProps> = ({
  status,
  type,
  className,
}) => {
  const getStatusVariant = () => {
    switch (status) {
      case 'OPEN':
        return 'position-open';
      case 'CLOSED':
        return 'position-closed';
      case 'PENDING':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getTypeVariant = () => {
    switch (type) {
      case 'BUY':
        return 'position-buy';
      case 'SELL':
        return 'position-sell';
      default:
        return 'default';
    }
  };

  return (
    <div className={cn('flex gap-2', className)}>
      <Badge variant={getTypeVariant()}>
        {type}
      </Badge>
      <Badge variant={getStatusVariant()}>
        {status}
      </Badge>
    </div>
  );
};
```

## Layout Patterns

### Dashboard Grid System
```typescript
// Dashboard layout with responsive grid
export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-background">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
        {/* Sidebar - 3 columns on large screens */}
        <div className="lg:col-span-3 hidden lg:block">
          <Sidebar />
        </div>

        {/* Main content - 9 columns on large screens */}
        <div className="lg:col-span-9 col-span-1">
          <main className="space-y-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};

// Widget grid for dashboard widgets
export const WidgetGrid: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {children}
    </div>
  );
};

// Widget with responsive sizing
export const DashboardWidget: React.FC<{
  title: string;
  size?: 'small' | 'medium' | 'large' | 'full';
  children: React.ReactNode;
}> = ({ title, size = 'medium', children }) => {
  const sizeClasses = {
    small: 'md:col-span-1',
    medium: 'md:col-span-2 xl:col-span-1',
    large: 'md:col-span-2 xl:col-span-2',
    full: 'md:col-span-2 xl:col-span-3',
  };

  return (
    <Card className={cn(sizeClasses[size])}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {children}
      </CardContent>
    </Card>
  );
};
```

### Responsive Navigation
```typescript
// Mobile-responsive navigation
export const Navigation: React.FC = () => {
  return (
    <nav className="bg-background border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and desktop navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <div className="flex-shrink-0">
              <img className="h-8 w-auto" src="/logo.svg" alt="Trading Bot" />
            </div>
            <div className="hidden md:flex space-x-4">
              <NavLink href="/dashboard">Dashboard</NavLink>
              <NavLink href="/positions">Positions</NavLink>
              <NavLink href="/portfolio">Portfolio</NavLink>
              <NavLink href="/risk">Risk</NavLink>
              <NavLink href="/settings">Settings</NavLink>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1">
            <MobileNavLink href="/dashboard">Dashboard</MobileNavLink>
            <MobileNavLink href="/positions">Positions</MobileNavLink>
            <MobileNavLink href="/portfolio">Portfolio</MobileNavLink>
            <MobileNavLink href="/risk">Risk</MobileNavLink>
            <MobileNavLink href="/settings">Settings</MobileNavLink>
          </div>
        </div>
      </div>
    </nav>
  );
};

const NavLink: React.FC<{ href: string; children: React.ReactNode }> = ({ href, children }) => {
  return (
    <a
      href={href}
      className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
    >
      {children}
    </a>
  );
};

const MobileNavLink: React.FC<{ href: string; children: React.ReactNode }> = ({ href, children }) => {
  return (
    <a
      href={href}
      className="text-gray-600 hover:text-gray-900 hover:bg-gray-50 block px-3 py-2 rounded-md text-base font-medium"
    >
      {children}
    </a>
  );
};
```

## Chart Styling

### Chart Configuration with Tailwind
```typescript
// Chart theme configuration
export const chartTheme = {
  colors: {
    background: 'transparent',
    text: 'hsl(var(--foreground))',
    primary: 'hsl(var(--primary))',
    secondary: 'hsl(var(--secondary))',
    profit: '#22c55e',
    loss: '#ef4444',
    buy: '#10b981',
    sell: '#f59e0b',
  },
  grid: {
    stroke: 'hsl(var(--border))',
    strokeDasharray: '3 3',
  },
  tooltip: {
    backgroundColor: 'hsl(var(--card))',
    borderColor: 'hsl(var(--border))',
    textStyle: {
      color: 'hsl(var(--foreground))',
    },
  },
};

// Chart wrapper with responsive sizing
export const ChartContainer: React.FC<{
  children: React.ReactNode;
  className?: string;
  height?: number;
}> = ({ children, className, height = 400 }) => {
  return (
    <div
      className={cn('w-full bg-card rounded-lg border border-border p-4', className)}
      style={{ height: height ? `${height}px` : 'auto' }}
    >
      {children}
    </div>
  );
};
```

## Custom Hooks for Styling

### Theme Management
```typescript
// src/hooks/use-theme.ts
import { useTheme } from 'next-themes';
import { useEffect } from 'react';

export const useTradingTheme = () => {
  const { theme, setTheme, systemTheme } = useTheme();

  useEffect(() => {
    // Apply custom CSS variables for trading theme
    const root = document.documentElement;

    if (theme === 'dark') {
      root.style.setProperty('--trading-bg', '#0f172a');
      root.style.setProperty('--trading-card', '#1e293b');
      root.style.setProperty('--trading-border', '#334155');
    } else {
      root.style.setProperty('--trading-bg', '#ffffff');
      root.style.setProperty('--trading-card', '#f8fafc');
      root.style.setProperty('--trading-border', '#e2e8f0');
    }
  }, [theme]);

  return {
    theme,
    setTheme,
    systemTheme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
  };
};
```

### Responsive Breakpoints
```typescript
// src/hooks/use-breakpoint.ts
import { useState, useEffect } from 'react';

export const useBreakpoint = () => {
  const [breakpoint, setBreakpoint] = useState({
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    isLargeDesktop: false,
  });

  useEffect(() => {
    const updateBreakpoint = () => {
      const width = window.innerWidth;
      setBreakpoint({
        isMobile: width < 768,
        isTablet: width >= 768 && width < 1024,
        isDesktop: width >= 1024 && width < 1280,
        isLargeDesktop: width >= 1280,
      });
    };

    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    return () => window.removeEventListener('resize', updateBreakpoint);
  }, []);

  return breakpoint;
};
```

## Animation System

### Trading Animations
```css
/* Custom animations for trading interface */
@keyframes pulse-success {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes pulse-error {
  0%, 100% {
    opacity: 1;
    background-color: #ef4444;
  }
  50% {
    opacity: 0.7;
    background-color: #dc2626;
  }
}

@keyframes slide-in-right {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slide-in-up {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes count-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Animation utilities */
.animate-pulse-success {
  animation: pulse-success 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-pulse-error {
  animation: pulse-error 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.animate-slide-in-right {
  animation: slide-in-right 0.3s ease-out;
}

.animate-slide-in-up {
  animation: slide-in-up 0.3s ease-out;
}

.animate-count-up {
  animation: count-up 0.5s ease-out;
}
```

### Animated Price Updates
```typescript
// src/components/ui/animated-price.tsx
import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface AnimatedPriceProps {
  value: number;
  previousValue?: number;
  className?: string;
}

export const AnimatedPrice: React.FC<AnimatedPriceProps> = ({
  value,
  previousValue,
  className,
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const [isAnimating, setIsAnimating] = useState(false);
  const [isPositive, setIsPositive] = useState(true);

  useEffect(() => {
    if (previousValue !== undefined && value !== previousValue) {
      setIsAnimating(true);
      setIsPositive(value > previousValue);

      // Animate number change
      const duration = 500;
      const start = previousValue;
      const end = value;
      const startTime = Date.now();

      const animate = () => {
        const now = Date.now();
        const progress = Math.min((now - startTime) / duration, 1);
        const current = start + (end - start) * progress;

        setDisplayValue(current);

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          setIsAnimating(false);
        }
      };

      requestAnimationFrame(animate);
    } else {
      setDisplayValue(value);
    }
  }, [value, previousValue]);

  return (
    <span className={cn(
      'transition-all duration-300',
      {
        'text-profit animate-count-up': isAnimating && isPositive,
        'text-loss animate-count-up': isAnimating && !isPositive,
      },
      className
    )}>
      {displayValue.toFixed(5)}
    </span>
  );
};
```

## Utility Classes

### Trading-Specific Utilities
```css
/* Trading layout utilities */
.trading-grid {
  @apply grid grid-cols-1 lg:grid-cols-12 gap-6;
}

.widget-small {
  @apply lg:col-span-3;
}

.widget-medium {
  @apply lg:col-span-6 xl:col-span-4;
}

.widget-large {
  @apply lg:col-span-9 xl:col-span-6;
}

.widget-full {
  @apply lg:col-span-12;
}

/* Trading status indicators */
.status-buy {
  @apply bg-buy text-white px-2 py-1 rounded-full text-xs font-semibold;
}

.status-sell {
  @apply bg-sell text-white px-2 py-1 rounded-full text-xs font-semibold;
}

.status-open {
  @apply bg-blue-500 text-white px-2 py-1 rounded-full text-xs font-semibold;
}

.status-closed {
  @apply bg-gray-500 text-white px-2 py-1 rounded-full text-xs font-semibold;
}

/* P&L display utilities */
.pnl-positive {
  @apply text-profit font-semibold;
}

.pnl-negative {
  @apply text-loss font-semibold;
}

.pnl-neutral {
  @apply text-muted-foreground font-semibold;
}

/* Risk level utilities */
.risk-low {
  @apply bg-risk-low/10 text-risk-low border border-risk-low/20;
}

.risk-medium {
  @apply bg-risk-medium/10 text-risk-medium border border-risk-medium/20;
}

.risk-high {
  @apply bg-risk-high/10 text-risk-high border border-risk-high/20;
}

.risk-critical {
  @apply bg-risk-critical/10 text-risk-critical border border-risk-critical/20;
}

/* Chart utilities */
.chart-container {
  @apply bg-card border border-border rounded-lg p-4;
}

.chart-legend {
  @apply flex flex-wrap gap-4 text-sm text-muted-foreground;
}

.chart-tooltip {
  @apply bg-card border border-border rounded-lg shadow-lg p-3 text-sm;
}

/* Form utilities for trading */
.trading-form {
  @apply space-y-6;
}

.form-section {
  @apply space-y-4;
}

.form-row {
  @apply grid grid-cols-1 md:grid-cols-2 gap-4;
}

.form-actions {
  @apply flex justify-end gap-3 pt-6 border-t border-border;
}

/* Table utilities for trading data */
.trading-table {
  @apply w-full border-collapse;
}

.trading-table th {
  @apply bg-muted/50 text-muted-foreground font-semibold px-4 py-3 text-left text-xs uppercase tracking-wider border-b border-border;
}

.trading-table td {
  @apply px-4 py-3 border-b border-border;
}

.trading-table tr:hover {
  @apply bg-muted/30;
}

.trading-table .profit-row {
  @apply bg-profit/5;
}

.trading-table .loss-row {
  @apply bg-loss/5;
}
```

## Dark Mode Implementation

### CSS Variables for Theming
```css
/* src/app/globals.css */
:root {
  /* Base colors */
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;
  --popover: 0 0% 100%;
  --popover-foreground: 222.2 84% 4.9%;
  --primary: 221.2 83.2% 53.3%;
  --primary-foreground: 210 40% 98%;
  --secondary: 210 40% 96%;
  --secondary-foreground: 222.2 84% 4.9%;
  --muted: 210 40% 96%;
  --muted-foreground: 215.4 16.3% 46.9%;
  --accent: 210 40% 96%;
  --accent-foreground: 222.2 84% 4.9%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 210 40% 98%;
  --border: 214.3 31.8% 91.4%;
  --input: 214.3 31.8% 91.4%;
  --ring: 221.2 83.2% 53.3%;
  --radius: 0.5rem;

  /* Trading specific colors */
  --trading-bg: 0 0% 100%;
  --trading-card: 0 0% 100%;
  --trading-border: 214.3 31.8% 91.4%;
  --chart-grid: 214.3 31.8% 91.4%;
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;
  --popover: 222.2 84% 4.9%;
  --popover-foreground: 210 40% 98%;
  --primary: 217.2 91.2% 59.8%;
  --primary-foreground: 222.2 84% 4.9%;
  --secondary: 217.2 32.6% 17.5%;
  --secondary-foreground: 210 40% 98%;
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;
  --accent: 217.2 32.6% 17.5%;
  --accent-foreground: 210 40% 98%;
  --destructive: 0 62.8% 30.6%;
  --destructive-foreground: 210 40% 98%;
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 224.3 76.3% 94.1%;

  /* Trading specific colors for dark mode */
  --trading-bg: 222.2 84% 4.9%;
  --trading-card: 217.2 32.6% 17.5%;
  --trading-border: 217.2 32.6% 17.5%;
  --chart-grid: 217.2 32.6% 17.5%;
}
```

### Theme Provider
```typescript
// src/components/providers/theme-provider.tsx
"use client";

import * as React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { type ThemeProviderProps } from 'next-themes/dist/types';

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

## Performance Optimization

### CSS Optimization
```javascript
// tailwind.config.js - Performance optimizations
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],

  // Purge CSS for production
  purge: {
    enabled: process.env.NODE_ENV === 'production',
    content: [
      './src/**/*.{js,ts,jsx,tsx}',
    ],
  },

  // Optimize for production
  prefix: '',
  important: false,
  separator: ':',

  theme: {
    // ... theme configuration
  },

  // Only include used utilities
  corePlugins: {
    preflight: true,
  },

  plugins: [
    // Only include plugins you actually use
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
};
```

### Bundle Optimization
```css
/* Critical CSS for above-the-fold content */
.critical-css {
  /* Only the most essential styles for initial render */
}

/* Lazy-loaded component styles */
.lazy-component {
  /* Styles loaded on demand */
}
```

This Tailwind CSS styling system provides a comprehensive, trading-focused design system with responsive layouts, custom components, dark mode support, and performance optimizations specifically tailored for financial dashboard applications.
