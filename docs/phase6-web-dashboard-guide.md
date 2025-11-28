# 🌐 Phase 6: Web Dashboard & UI Implementation Guide

## Overview

**Phase 6** focuses on building a modern web-based trading dashboard using **Next.js 14+**, **Tailwind CSS**, and **FastAPI** to provide a user-friendly interface for the Advanced Trading Bot System.

## Technology Stack

### Frontend Architecture
- **Next.js 14+** with App Router for modern React development
- **Tailwind CSS** for utility-first styling and responsive design
- **TypeScript** for type safety and better development experience
- **Recharts** for data visualization and trading charts
- **React Query/TanStack Query** for server state management
- **Zustand** for client-side state management
- **React Hook Form** for form handling and validation

### Backend Integration
- **FastAPI** for REST API endpoints
- **JWT Authentication** for secure access
- **CORS Configuration** for cross-origin requests
- **API Rate Limiting** for security
- **Real-time Polling** for live data updates

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js App   │    │   FastAPI       │    │  Trading Bot    │
│   (Frontend)    │◄──►│   Backend API   │◄──►│   Core System   │
│                 │    │                 │    │                 │
│ - Dashboard UI  │    │ - REST Endpoints│    │ - Strategy Mgr  │
│ - Charts        │    │ - Auth/JWT      │    │ - Risk Mgmt     │
│ - Forms         │    │ - Rate Limiting │    │ - Position Mgr  │
│ - Real-time     │    │ - Data Aggregation│   │ - MT5 Connector │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
phase6-web-dashboard/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   │   ├── (dashboard)/    # Dashboard route group
│   │   │   │   ├── page.tsx    # Main dashboard
│   │   │   │   ├── positions/  # Position management
│   │   │   │   ├── portfolio/  # Portfolio overview
│   │   │   │   ├── risk/       # Risk monitoring
│   │   │   │   └── settings/   # Configuration
│   │   │   ├── auth/          # Authentication pages
│   │   │   └── globals.css    # Global styles
│   │   ├── components/         # Reusable components
│   │   │   ├── ui/            # Base UI components
│   │   │   ├── charts/        # Chart components
│   │   │   ├── forms/         # Form components
│   │   │   └── layout/        # Layout components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utility functions
│   │   ├── types/             # TypeScript type definitions
│   │   └── store/             # Zustand state stores
│   ├── public/                # Static assets
│   ├── tailwind.config.js     # Tailwind configuration
│   ├── next.config.js         # Next.js configuration
│   └── package.json          # Dependencies
├── api/                     # FastAPI backend
│   ├── app/
│   │   ├── api/              # API routes
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── dashboard.py  # Dashboard data endpoints
│   │   │   ├── positions.py  # Position management
│   │   │   ├── portfolio.py  # Portfolio data
│   │   │   └── settings.py   # Configuration APIs
│   │   ├── core/             # Core functionality
│   │   │   ├── auth.py       # Authentication logic
│   │   │   ├── security.py   # Security utilities
│   │   │   └── config.py    # API configuration
│   │   ├── models/           # Pydantic models
│   │   └── services/         # Business logic services
│   └── requirements.txt      # Python dependencies
└── docker-compose.yml        # Development environment
```

## Implementation Phases

### Phase 6.1: Project Setup & Foundation (Week 1)

#### Frontend Setup
```bash
# Create Next.js project with TypeScript
npx create-next-app@latest trading-bot-dashboard --typescript --tailwind --app

# Install required dependencies
npm install @tanstack/react-query zustand react-hook-form @hookform/resolvers zod
npm install recharts lucide-react clsx tailwind-merge class-variance-authority
npm install axios date-fns

# Install dev dependencies
npm install -D @types/node eslint eslint-config-next
```

#### Backend Setup
```bash
# Create API directory and install FastAPI
mkdir api && cd api
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt]
pip install python-multipart slowapi aiosqlite sqlalchemy

# Install trading bot integration
pip install -e ../src/
```

### Phase 6.2: Authentication & Security (Week 1)

#### JWT Authentication System
- Secure login/logout functionality
- Token-based authentication
- Protected routes and API endpoints
- Session management with refresh tokens

#### Security Implementation
- CORS configuration for development/production
- API rate limiting to prevent abuse
- Input validation and sanitization
- Environment variable management for secrets

### Phase 6.3: Dashboard Core Features (Week 2)

#### Portfolio Overview
- Real-time P&L tracking with charts
- Asset allocation pie charts
- Performance metrics (Sharpe ratio, max drawdown)
- Account balance visualization

#### Position Management
- Active positions table with real-time updates
- Position details (entry, SL, TP, current P&L)
- Manual position adjustment controls
- Position history with filtering

#### Risk Monitoring
- Real-time risk metrics dashboard
- Risk exposure charts and heatmaps
- Alert history and status
- Correlation matrix visualization

### Phase 6.4: Trading Interface (Week 2)

#### Market Data Visualization
- Live price charts with technical indicators
- Multi-timeframe chart views
- Supply & Demand zone overlays
- Technical indicator integration

#### Manual Trading Features
- Order placement forms (market, limit, stop)
- Position size calculator
- Risk/reward visualization
- One-click position management

### Phase 6.5: Configuration Management (Week 3)

#### Strategy Configuration
- Trading type selection (scalping, day, swing, position)
- Strategy parameter adjustment
- Technical indicator settings
- Risk management parameters

#### System Settings
- Notification preferences (Telegram, email)
- API key management
- Database connection settings
- Trading schedule configuration

### Phase 6.6: Advanced Features (Week 3)

#### Analytics & Reporting
- Trade history analysis
- Performance attribution
- Export functionality (CSV, PDF)
- Custom date range reporting

#### Real-time Features
- WebSocket integration for live updates
- Price alert notifications
- System status monitoring
- Automated trading controls

## Technical Implementation Details

### Next.js Configuration

#### `next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

#### Tailwind Configuration
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        success: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        danger: {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
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
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### FastAPI Backend Setup

#### Main Application
```python
# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.api import auth, dashboard, positions, portfolio, settings
from app.core.config import settings

app = FastAPI(
    title="Trading Bot API",
    description="REST API for Trading Bot Dashboard",
    version="1.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "trading-bot-api"}
```

#### Authentication Service
```python
# api/app/core/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

## Integration with Trading Bot

### Data Models

#### TypeScript Types
```typescript
// src/types/trading.ts
export interface Position {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  volume: number;
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  currentPrice: number;
  profit: number;
  profitPips: number;
  openTime: string;
  status: 'OPEN' | 'CLOSED';
}

export interface PortfolioSummary {
  totalBalance: number;
  totalEquity: number;
  totalProfit: number;
  totalProfitPercent: number;
  openPositions: number;
  dailyPL: number;
  maxDrawdown: number;
  sharpeRatio: number;
}

export interface RiskMetrics {
  currentRisk: number;
  maxRisk: number;
  riskUtilization: number;
  correlationScore: number;
  exposureBreakdown: Record<string, number>;
}
```

#### API Response Models
```python
# api/app/models/dashboard.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PositionResponse(BaseModel):
    id: str
    symbol: str
    type: str
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    current_price: float
    profit: float
    profit_pips: float
    open_time: datetime
    status: str

class PortfolioSummaryResponse(BaseModel):
    total_balance: float
    total_equity: float
    total_profit: float
    total_profit_percent: float
    open_positions: int
    daily_pl: float
    max_drawdown: float
    sharpe_ratio: float

class RiskMetricsResponse(BaseModel):
    current_risk: float
    max_risk: float
    risk_utilization: float
    correlation_score: float
    exposure_breakdown: dict
```

### Real-time Data Integration

#### React Query Configuration
```typescript
// src/lib/react-query.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 5000, // 5 seconds for real-time data
      retry: 3,
      staleTime: 1000,
    },
  },
});

// Custom hooks
export const usePositions = () => {
  return useQuery({
    queryKey: ['positions'],
    queryFn: async () => {
      const response = await fetch('/api/positions');
      if (!response.ok) {
        throw new Error('Failed to fetch positions');
      }
      return response.json();
    },
  });
};

export const usePortfolio = () => {
  return useQuery({
    queryKey: ['portfolio'],
    queryFn: async () => {
      const response = await fetch('/api/portfolio');
      if (!response.ok) {
        throw new Error('Failed to fetch portfolio data');
      }
      return response.json();
    },
  });
};
```

## Development Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+ and pip
- Trading Bot system (Phase 1-5 completed)

### Local Development

#### 1. Environment Setup
```bash
# Clone project and setup frontend
git clone <project-url>
cd phase6-web-dashboard/frontend
npm install

# Setup backend API
cd ../api
pip install -r requirements.txt
```

#### 2. Environment Configuration
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# Backend (.env)
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_HOSTS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

#### 3. Development Servers
```bash
# Start FastAPI backend (terminal 1)
cd api
uvicorn app.main:app --reload --port 8000

# Start Next.js frontend (terminal 2)
cd frontend
npm run dev
```

#### 4. Trading Bot Integration
```bash
# Start trading bot with API mode enabled
cd ../../
uv run trading-bot start --config production --api-mode
```

## Security Considerations

### Authentication & Authorization
- JWT-based authentication with secure token handling
- Role-based access control (admin, trader, viewer)
- API key management for third-party integrations
- Session timeout and refresh token rotation

### API Security
- CORS configuration for cross-origin requests
- Rate limiting to prevent API abuse
- Input validation and SQL injection prevention
- HTTPS enforcement in production

### Data Protection
- Environment variable encryption
- Database connection security
- Sensitive data redaction in logs
- Backup encryption and secure storage

## Performance Optimization

### Frontend Optimization
- Code splitting with dynamic imports
- Image optimization and lazy loading
- Bundle size analysis and optimization
- Service worker for offline functionality

### Backend Optimization
- Database query optimization
- Redis caching for frequent requests
- Async request handling
- Connection pooling for database

### Real-time Updates
- Efficient polling strategies
- WebSocket integration for critical updates
- Data compression and optimization
- CDN integration for static assets

## Testing Strategy

### Frontend Testing
```bash
# Install testing dependencies
npm install -D jest @testing-library/react @testing-library/jest-dom

# Run tests
npm run test
npm run test:coverage
```

### Backend Testing
```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest api/tests/
pytest --cov=api tests/
```

### Integration Testing
- End-to-end testing with Playwright
- API integration testing with fixtures
- Mock trading bot responses for development
- Performance testing with load simulation

## Deployment

### Docker Development
```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

  backend:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-secret-key
      - ALLOWED_HOSTS=["http://localhost:3000"]
    volumes:
      - ./api:/app
    depends_on:
      - trading-bot

  trading-bot:
    build: ../
    command: python -m trading_bot.main --config production --api-mode
    volumes:
      - ../:/app
      - ./data:/app/data
```

### Production Deployment
- Vercel for Next.js frontend deployment
- Railway/Heroku for FastAPI backend
- Environment-specific configuration
- SSL certificates and HTTPS enforcement
- Monitoring and logging integration

## Success Metrics

### Technical Metrics
- Page load time < 2 seconds
- API response time < 500ms
- 99.9% uptime availability
- Mobile responsiveness score > 90
- Core Web Vitals compliance

### User Experience Metrics
- Intuitive navigation and usability
- Real-time data accuracy < 5 seconds latency
- Zero data loss during trading operations
- Comprehensive error handling and recovery
- Accessibility compliance (WCAG 2.1)

### Integration Metrics
- Seamless trading bot integration
- Complete feature parity with CLI interface
- Reliable real-time data synchronization
- Secure authentication and authorization
- Scalable architecture for multiple users

---

**Phase 6 transforms the advanced trading bot system into a professional web application, providing an intuitive interface for monitoring, managing, and controlling automated trading operations.**