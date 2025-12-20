# 🔌 FastAPI Backend Integration Guide

## Overview

This document provides comprehensive guidance for implementing the FastAPI backend that integrates with the existing Trading Bot system, providing RESTful APIs for the Next.js dashboard.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI       │    │  Trading Bot   │
│   Frontend      │◄──►│   Backend       │◄──►│   Core System   │
│                 │    │                 │    │                 │
│ - Dashboard UI  │    │ - REST API      │    │ - Strategy Mgr  │
│ - Charts        │    │ - Auth/JWT      │    │ - Risk Mgmt     │
│ - Real-time     │    │ - Rate Limiting │    │ - Position Mgr  │
│ - Forms         │    │ - Validation    │    │ - Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
api/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/                   # API route modules
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── dashboard.py       # Dashboard data endpoints
│   │   ├── positions.py       # Position management endpoints
│   │   ├── portfolio.py       # Portfolio data endpoints
│   │   ├── trading.py         # Trading operations endpoints
│   │   ├── risk.py            # Risk management endpoints
│   │   ├── settings.py        # Configuration endpoints
│   │   └── analytics.py       # Analytics and reporting endpoints
│   ├── core/                  # Core application functionality
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── security.py        # Security utilities
│   │   ├── auth.py           # Authentication logic
│   │   ├── database.py        # Database connection
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── middleware.py     # Custom middleware
│   ├── models/                # Pydantic data models
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication models
│   │   ├── trading.py        # Trading data models
│   │   ├── portfolio.py      # Portfolio models
│   │   ├── risk.py           # Risk management models
│   │   └── common.py        # Common data models
│   ├── services/              # Business logic services
│   │   ├── __init__.py
│   │   ├── trading_service.py # Trading operations
│   │   ├── portfolio_service.py # Portfolio management
│   │   ├── risk_service.py   # Risk calculations
│   │   ├── analytics_service.py # Analytics and reporting
│   │   └── notification_service.py # Notification management
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── datetime_utils.py  # Date/time utilities
│       ├── calculation_utils.py # Financial calculations
│       └── validation_utils.py # Data validation
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Test configuration
│   ├── test_auth.py          # Authentication tests
│   ├── test_api.py           # API endpoint tests
│   ├── test_services.py      # Service layer tests
│   └── test_integration.py   # Integration tests
├── requirements.txt           # Python dependencies
├── .env.example             # Environment variables template
└── dockerfile               # Docker configuration
```

## Dependencies Setup

### `requirements.txt`

```txt
# FastAPI and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
aiosqlite==0.19.0
alembic==1.12.1

# Rate limiting and caching
slowapi==0.7.2
redis==5.0.1

# Data validation and serialization
pydantic==2.5.0
pydantic-settings==2.1.0

# HTTP client for external services
httpx==0.25.2

# Utilities
python-dotenv==1.0.0
loguru==0.7.2
typer==0.9.0

# Trading bot integration (existing system)
# Add trading bot package as editable install
# -e ../src

# Development dependencies
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
ruff==0.1.6
mypy==1.7.1
```

## Configuration Management

### `.env.example`

```env
# Application
APP_NAME="Trading Bot API"
APP_VERSION="1.0.0"
DEBUG=false
SECRET_KEY="your-super-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=false

# Database
DATABASE_URL="sqlite+aiosqlite:///./trading_bot.db"
DATABASE_ECHO=false

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
ALLOWED_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS=["*"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60  # seconds

# Redis (for caching, optional)
REDIS_URL="redis://localhost:6379/0"
REDIS_ENABLED=false

# Trading Bot Integration
TRADING_BOT_CONFIG_PATH="../config/production.yaml"
TRADING_BOT_API_MODE=true

# Logging
LOG_LEVEL="INFO"
LOG_FORMAT="json"
LOG_FILE="logs/api.log"

# Notifications
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
TELEGRAM_CHAT_ID="your-chat-id"
EMAIL_ENABLED=false
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
```

### Core Configuration

```python
# api/app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Trading Bot API"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./trading_bot.db"
    database_echo: bool = False

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000"]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: List[str] = ["*"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False

    # Trading Bot Integration
    trading_bot_config_path: str = "../config/production.yaml"
    trading_bot_api_mode: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/api.log"

    # Notifications
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Main Application Setup

### `api/app/main.py`

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api import (
    auth,
    dashboard,
    positions,
    portfolio,
    trading,
    risk,
    settings as settings_api,
    analytics,
)
from app.core.exceptions import TradingBotAPIException

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Trading Bot API...")
    await init_db()
    logger.info("Database initialized")

    # Initialize trading bot connection
    try:
        from app.services.trading_service import TradingService
        trading_service = TradingService()
        await trading_service.initialize()
        logger.info("Trading bot service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize trading bot: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Trading Bot API...")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="REST API for Trading Bot Dashboard",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Exception handlers
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(TradingBotAPIException, trading_bot_exception_handler)

# Middleware
app.state.limiter = limiter

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Trusted hosts middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", settings.host.split(":")[0]]
)

# Include routers
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["authentication"]
)
app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["dashboard"]
)
app.include_router(
    positions.router,
    prefix="/api/positions",
    tags=["positions"]
)
app.include_router(
    portfolio.router,
    prefix="/api/portfolio",
    tags=["portfolio"]
)
app.include_router(
    trading.router,
    prefix="/api/trading",
    tags=["trading"]
)
app.include_router(
    risk.router,
    prefix="/api/risk",
    tags=["risk"]
)
app.include_router(
    settings_api.router,
    prefix="/api/settings",
    tags=["settings"]
)
app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["analytics"]
)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )

    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/api/health")
@limiter.limit("100/minute")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "trading-bot-api",
        "version": settings.app_version,
        "debug": settings.debug,
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Bot API",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation not available in production",
    }

def trading_bot_exception_handler(request: Request, exc: TradingBotAPIException):
    """Custom exception handler for trading bot errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
```

## Authentication System

### JWT Authentication

```python
# api/app/core/auth.py
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.auth import User, TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(
            username=username,
            user_id=user_id,
            role=role
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    token_data = verify_token(token)

    # In a real application, you would fetch user from database
    # For now, return a mock user
    user = User(
        id=token_data.user_id,
        username=token_data.username,
        role=token_data.role,
    )

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    # Add user status check if needed
    return current_user

def require_role(required_role: Union[str, list]):
    """Decorator to require specific user role"""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if isinstance(required_role, list):
            if current_user.role not in required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        else:
            if current_user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        return current_user

    return role_checker
```

### Authentication Routes

```python
# api/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import timedelta

from app.core.auth import (
    verify_password,
    create_access_token,
    get_password_hash,
    get_current_active_user,
)
from app.core.config import settings
from app.models.auth import User, LoginRequest, LoginResponse
from app.core.exceptions import TradingBotAPIException

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Mock user database (in production, use real database)
USERS_DB = {
    "admin": {
        "id": "1",
        "username": "admin",
        "email": "admin@tradingbot.com",
        "role": "admin",
        "hashed_password": get_password_hash("admin123"),  # Change in production
    },
    "trader": {
        "id": "2",
        "username": "trader",
        "email": "trader@tradingbot.com",
        "role": "trader",
        "hashed_password": get_password_hash("trader123"),  # Change in production
    }
}

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Limit login attempts
async def login(request, credentials: LoginRequest):
    """Authenticate user and return access token"""
    # Validate credentials
    user_data = USERS_DB.get(credentials.username)

    if not user_data or not verify_password(
        credentials.password,
        user_data["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"],
        },
        expires_delta=access_token_expires,
    )

    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        role=user_data["role"],
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": current_user.username,
            "user_id": current_user.id,
            "role": current_user.role,
        },
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout user (invalidate token)"""
    # In a real application, you would invalidate the token
    # For JWT, this would require maintaining a blacklist
    return {"message": "Successfully logged out"}
```

## Data Models

### Trading Models

```python
# api/app/models/trading.py
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum

class PositionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"

class Position(BaseModel):
    id: str
    symbol: str = Field(..., description="Trading symbol")
    type: PositionType = Field(..., description="Position type")
    volume: float = Field(..., gt=0, description="Position volume in lots")
    entry_price: float = Field(..., gt=0, description="Entry price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    current_price: float = Field(..., gt=0, description="Current market price")
    profit: float = Field(..., description="Current profit in account currency")
    profit_pips: float = Field(..., description="Current profit in pips")
    open_time: datetime = Field(..., description="Position open time")
    close_time: Optional[datetime] = Field(None, description="Position close time")
    status: PositionStatus = Field(..., description="Position status")
    commission: Optional[float] = Field(None, description="Commission charged")
    swap: Optional[float] = Field(None, description="Swap charges")
    comment: Optional[str] = Field(None, description="Position comment")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PositionCreate(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    type: PositionType = Field(..., description="Position type")
    volume: float = Field(..., gt=0, le=100, description="Position volume in lots")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")
    comment: Optional[str] = Field(None, description="Position comment")

class PositionUpdate(BaseModel):
    stop_loss: Optional[float] = Field(None, gt=0, description="New stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="New take profit price")
    comment: Optional[str] = Field(None, description="Position comment")

class PositionClose(BaseModel):
    reason: Optional[str] = Field(None, description="Close reason")

class TradeSignal(BaseModel):
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float = Field(..., ge=0, le=100)
    foundation_score: float = Field(..., ge=0, le=100)
    confluence_score: float = Field(..., ge=0, le=100)
    risk_reward_ratio: float = Field(..., gt=0)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime
    strategy_layers: dict = {}
    analysis_timeframe: str
    trading_type: str

class Order(BaseModel):
    id: str
    symbol: str
    type: str  # LIMIT, STOP, MARKET
    order_type: PositionType
    volume: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    created_time: datetime
    executed_time: Optional[datetime] = None
    comment: Optional[str] = None
```

### Portfolio Models

```python
# api/app/models/portfolio.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class PortfolioSummary(BaseModel):
    total_balance: float = Field(..., ge=0, description="Total account balance")
    total_equity: float = Field(..., ge=0, description="Total equity including unrealized P&L")
    total_profit: float = Field(..., description="Total profit/loss")
    total_profit_percent: float = Field(..., description="Total profit as percentage")
    available_margin: float = Field(..., ge=0, description="Available margin for trading")
    margin_used: float = Field(..., ge=0, description="Margin currently used")
    margin_level: float = Field(..., ge=0, description="Margin level percentage")
    open_positions: int = Field(..., ge=0, description="Number of open positions")
    daily_pl: float = Field(..., description="Daily profit/loss")
    weekly_pl: float = Field(..., description="Weekly profit/loss")
    monthly_pl: float = Field(..., description="Monthly profit/loss")

class AssetAllocation(BaseModel):
    asset_class: str
    allocated_percentage: float
    allocated_amount: float
    pnl: float
    pnl_percentage: float

class PerformanceMetrics(BaseModel):
    total_return: float
    annualized_return: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: float
    max_drawdown_percent: float
    calmar_ratio: Optional[float] = None
    win_rate: float = Field(..., ge=0, le=1, description="Win rate percentage")
    profit_factor: float = Field(..., gt=0, description="Profit factor")
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int

class DailyBalance(BaseModel):
    date: datetime
    balance: float
    equity: float
    profit: float
    positions_count: int

class PortfolioAnalytics(BaseModel):
    summary: PortfolioSummary
    asset_allocation: List[AssetAllocation]
    performance: PerformanceMetrics
    daily_balances: List[DailyBalance]
    correlation_matrix: Dict[str, Dict[str, float]]
```

## API Endpoints Implementation

### Position Management

```python
# api/app/api/positions.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth import get_current_active_user, require_role
from app.models.auth import User
from app.models.trading import Position, PositionCreate, PositionUpdate, PositionClose
from app.services.trading_service import TradingService
from app.core.exceptions import TradingBotAPIException

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get("/", response_model=List[Position])
@limiter.limit("100/minute")
async def get_positions(
    request,
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=1000, description="Number of positions to return"),
    offset: int = Query(0, ge=0, description="Number of positions to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """Get all positions with optional filtering"""
    try:
        trading_service = TradingService()
        positions = await trading_service.get_positions(
            user_id=current_user.id,
            status=status,
            symbol=symbol,
            limit=limit,
            offset=offset
        )
        return positions
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to retrieve positions",
            error_code="POSITIONS_RETRIEVAL_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{position_id}", response_model=Position)
@limiter.limit("100/minute")
async def get_position(
    request,
    position_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific position by ID"""
    try:
        trading_service = TradingService()
        position = await trading_service.get_position(
            position_id=position_id,
            user_id=current_user.id
        )

        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found"
            )

        return position
    except HTTPException:
        raise
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to retrieve position",
            error_code="POSITION_RETRIEVAL_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/", response_model=Position)
@limiter.limit("20/minute")
async def create_position(
    request,
    position_data: PositionCreate,
    current_user: User = Depends(require_role(["admin", "trader"]))
):
    """Create new position"""
    try:
        trading_service = TradingService()
        position = await trading_service.create_position(
            position_data=position_data,
            user_id=current_user.id
        )
        return position
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to create position",
            error_code="POSITION_CREATION_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.put("/{position_id}", response_model=Position)
@limiter.limit("50/minute")
async def update_position(
    request,
    position_id: str,
    position_update: PositionUpdate,
    current_user: User = Depends(require_role(["admin", "trader"]))
):
    """Update existing position"""
    try:
        trading_service = TradingService()
        position = await trading_service.update_position(
            position_id=position_id,
            position_update=position_update,
            user_id=current_user.id
        )

        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found"
            )

        return position
    except HTTPException:
        raise
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to update position",
            error_code="POSITION_UPDATE_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/{position_id}/close")
@limiter.limit("30/minute")
async def close_position(
    request,
    position_id: str,
    close_data: PositionClose,
    current_user: User = Depends(require_role(["admin", "trader"]))
):
    """Close position"""
    try:
        trading_service = TradingService()
        success = await trading_service.close_position(
            position_id=position_id,
            close_reason=close_data.reason,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found or already closed"
            )

        return {"message": "Position closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to close position",
            error_code="POSITION_CLOSE_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### Portfolio Data

```python
# api/app/api/portfolio.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.auth import get_current_active_user
from app.models.auth import User
from app.models.portfolio import PortfolioSummary, PortfolioAnalytics
from app.services.portfolio_service import PortfolioService
from app.core.exceptions import TradingBotAPIException

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get("/summary", response_model=PortfolioSummary)
@limiter.limit("100/minute")
async def get_portfolio_summary(
    request,
    current_user: User = Depends(get_current_active_user)
):
    """Get portfolio summary"""
    try:
        portfolio_service = PortfolioService()
        summary = await portfolio_service.get_summary(user_id=current_user.id)
        return summary
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to retrieve portfolio summary",
            error_code="PORTFOLIO_SUMMARY_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/analytics", response_model=PortfolioAnalytics)
@limiter.limit("50/minute")
async def get_portfolio_analytics(
    request,
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    current_user: User = Depends(get_current_active_user)
):
    """Get portfolio analytics"""
    try:
        portfolio_service = PortfolioService()

        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        analytics = await portfolio_service.get_analytics(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        return analytics
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to retrieve portfolio analytics",
            error_code="PORTFOLIO_ANALYTICS_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/daily-balances")
@limiter.limit("100/minute")
async def get_daily_balances(
    request,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_active_user)
):
    """Get daily balance history"""
    try:
        portfolio_service = PortfolioService()
        balances = await portfolio_service.get_daily_balances(
            user_id=current_user.id,
            days=days
        )
        return balances
    except Exception as e:
        raise TradingBotAPIException(
            message="Failed to retrieve daily balances",
            error_code="DAILY_BALANCES_ERROR",
            details=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

## Trading Bot Integration Service

### Main Trading Service

```python
# api/app/services/trading_service.py
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import sys
import os

# Add the trading bot source to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

try:
    from trading_bot.main import TradingBot
    from trading_bot.config import ConfigManager
    from trading_bot.core import Position, TradeSignal
except ImportError as e:
    print(f"Warning: Could not import trading bot modules: {e}")
    TradingBot = None
    ConfigManager = None

from app.models.trading import Position as APIPosition, PositionCreate, PositionUpdate
from app.core.exceptions import TradingBotAPIException
from app.core.config import settings

class TradingService:
    """Service for integrating with the Trading Bot system"""

    def __init__(self):
        self.trading_bot = None
        self.config_manager = None
        self._initialized = False

    async def initialize(self):
        """Initialize trading bot connection"""
        if self._initialized:
            return

        try:
            if TradingBot is None or ConfigManager is None:
                raise ImportError("Trading bot modules not available")

            # Load trading bot configuration
            self.config_manager = ConfigManager()
            await self.config_manager.load_config(settings.trading_bot_config_path)

            # Initialize trading bot
            self.trading_bot = TradingBot(config_manager=self.config_manager)
            await self.trading_bot.initialize()

            self._initialized = True

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to initialize trading bot service",
                error_code="TRADING_BOT_INIT_ERROR",
                details=str(e),
                status_code=500
            )

    def _ensure_initialized(self):
        """Ensure service is initialized"""
        if not self._initialized:
            raise TradingBotAPIException(
                message="Trading service not initialized",
                error_code="SERVICE_NOT_INITIALIZED",
                details="Service must be initialized before use",
                status_code=503
            )

    def _convert_position_to_api(self, bot_position: Position) -> APIPosition:
        """Convert trading bot position to API position model"""
        return APIPosition(
            id=bot_position.position_id,
            symbol=bot_position.symbol,
            type=bot_position.type,
            volume=bot_position.volume,
            entry_price=bot_position.entry_price,
            stop_loss=bot_position.stop_loss,
            take_profit=bot_position.take_profit,
            current_price=bot_position.current_price,
            profit=bot_position.current_pnl,
            profit_pips=bot_position.current_profit_pips,
            open_time=bot_position.open_time,
            close_time=bot_position.close_time,
            status=bot_position.status,
            commission=bot_position.commission,
            swap=bot_position.swap,
            comment=bot_position.comment
        )

    async def get_positions(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[APIPosition]:
        """Get positions from trading bot"""
        self._ensure_initialized()

        try:
            # Get positions from trading bot
            bot_positions = await self.trading_bot.position_manager.get_all_positions()

            # Apply filters
            filtered_positions = []
            for pos in bot_positions:
                # Status filter
                if status and pos.status != status:
                    continue

                # Symbol filter
                if symbol and pos.symbol != symbol:
                    continue

                filtered_positions.append(pos)

            # Apply pagination
            paginated_positions = filtered_positions[offset:offset + limit]

            # Convert to API models
            api_positions = [
                self._convert_position_to_api(pos)
                for pos in paginated_positions
            ]

            return api_positions

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to get positions from trading bot",
                error_code="POSITIONS_FETCH_ERROR",
                details=str(e),
                status_code=500
            )

    async def get_position(self, position_id: str, user_id: str) -> Optional[APIPosition]:
        """Get specific position from trading bot"""
        self._ensure_initialized()

        try:
            bot_position = await self.trading_bot.position_manager.get_position(position_id)

            if not bot_position:
                return None

            return self._convert_position_to_api(bot_position)

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to get position from trading bot",
                error_code="POSITION_FETCH_ERROR",
                details=str(e),
                status_code=500
            )

    async def create_position(self, position_data: PositionCreate, user_id: str) -> APIPosition:
        """Create new position via trading bot"""
        self._ensure_initialized()

        try:
            # Create position through trading bot
            position_params = {
                'symbol': position_data.symbol,
                'type': position_data.type,
                'volume': position_data.volume,
                'stop_loss': position_data.stop_loss,
                'take_profit': position_data.take_profit,
                'comment': position_data.comment
            }

            bot_position = await self.trading_bot.execute_manual_trade(position_params)

            return self._convert_position_to_api(bot_position)

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to create position in trading bot",
                error_code="POSITION_CREATION_ERROR",
                details=str(e),
                status_code=500
            )

    async def update_position(
        self,
        position_id: str,
        position_update: PositionUpdate,
        user_id: str
    ) -> Optional[APIPosition]:
        """Update position via trading bot"""
        self._ensure_initialized()

        try:
            # Update position through trading bot
            update_params = {}

            if position_update.stop_loss is not None:
                update_params['stop_loss'] = position_update.stop_loss

            if position_update.take_profit is not None:
                update_params['take_profit'] = position_update.take_profit

            if position_update.comment is not None:
                update_params['comment'] = position_update.comment

            bot_position = await self.trading_bot.position_manager.modify_position(
                position_id=position_id,
                **update_params
            )

            if not bot_position:
                return None

            return self._convert_position_to_api(bot_position)

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to update position in trading bot",
                error_code="POSITION_UPDATE_ERROR",
                details=str(e),
                status_code=500
            )

    async def close_position(
        self,
        position_id: str,
        close_reason: Optional[str] = None,
        user_id: str
    ) -> bool:
        """Close position via trading bot"""
        self._ensure_initialized()

        try:
            success = await self.trading_bot.position_manager.close_position(
                position_id=position_id,
                reason=close_reason or "Manual close via API"
            )

            return success

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to close position in trading bot",
                error_code="POSITION_CLOSE_ERROR",
                details=str(e),
                status_code=500
            )

    async def get_signals(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current trading signals from trading bot"""
        self._ensure_initialized()

        try:
            signals = await self.trading_bot.strategy_manager.get_current_signals()

            # Apply symbol filter
            if symbol:
                signals = [s for s in signals if s.symbol == symbol]

            # Convert to dictionaries for JSON response
            return [
                {
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type,
                    'confidence': signal.confidence,
                    'foundation_score': signal.foundation_score,
                    'confluence_score': signal.confluence_score,
                    'risk_reward_ratio': signal.risk_reward_ratio,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timestamp': signal.timestamp.isoformat(),
                    'strategy_layers': signal.strategy_layers,
                    'analysis_timeframe': signal.analysis_timeframe,
                    'trading_type': signal.trading_type,
                }
                for signal in signals
            ]

        except Exception as e:
            raise TradingBotAPIException(
                message="Failed to get signals from trading bot",
                error_code="SIGNALS_FETCH_ERROR",
                details=str(e),
                status_code=500
            )
```

## Testing

### API Integration Tests

```python
# api/tests/test_integration.py
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

class TestTradingAPI:
    """Integration tests for trading API endpoints"""

    @pytest.fixture
    async def client(self):
        """Test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def auth_headers(self, client):
        """Get authenticated headers"""
        # Login and get token
        login_data = {
            "username": "trader",
            "password": "trader123"
        }
        response = await client.post("/api/auth/login", json=login_data)
        token = response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "trading-bot-api"

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login"""
        login_data = {
            "username": "trader",
            "password": "trader123"
        }
        response = await client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "trader"

    @pytest.mark.asyncio
    async def test_get_positions(self, client, auth_headers):
        """Test getting positions"""
        response = await client.get(
            "/api/positions/",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_portfolio_summary(self, client, auth_headers):
        """Test getting portfolio summary"""
        response = await client.get(
            "/api/portfolio/summary",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_balance" in data
        assert "total_equity" in data
        assert "open_positions" in data

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client):
        """Test unauthorized access"""
        response = await client.get("/api/positions/")
        assert response.status_code == 401

        data = response.json()
        assert "detail" in data
```

## Deployment

### Docker Configuration

```dockerfile
# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./trading_bot.db
      - SECRET_KEY=your-super-secret-key
      - DEBUG=false
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./api:/app
      - ./data:/app/data
    depends_on:
      - redis
    networks:
      - trading-bot-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - trading-bot-network

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
      - api
    networks:
      - trading-bot-network

networks:
  trading-bot-network:
    driver: bridge
```

This FastAPI backend integration provides a robust, secure, and scalable API layer for the trading dashboard, with comprehensive authentication, rate limiting, error handling, and full integration with the existing trading bot system.
