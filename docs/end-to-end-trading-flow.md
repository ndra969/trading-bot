# End-to-End Trading Flow Documentation

## Overview

This document provides a comprehensive overview of the complete trading flow in the Advanced Trading Bot System, from market analysis to trade execution and management.

## 🏗️ System Architecture Flow

```mermaid
graph TB
    subgraph "User Interface"
        CLI[CLI Commands]
        Config[Configuration Files]
    end

    subgraph "Core System"
        Main[TradingBot Main]
        Engine[Trading Engine]
        Scheduler[Task Scheduler]
    end

    subgraph "Market Analysis"
        MH[Market Hours Validator]
        MA[Market Analysis Engine]
        SD[Supply & Demand Analysis]
        PA[Price Action Analysis]
        FIB[Fibonacci Analysis]
        RSI[RSI Analysis]
        MV[Moving Average Analysis]
    end

    subgraph "Trading Logic"
        CS[Confluence Scoring]
        RM[Risk Management]
        PS[Position Sizing]
        PC[Pip Calculator]
    end

    subgraph "Execution"
        MT5[MT5 Connector]
        Mock[Mock Trading]
        Order[Order Management]
    end

    subgraph "Data Layer"
        DB[(SQLite Database)]
        Repo[Repositories]
        Models[Data Models]
    end

    subgraph "External Systems"
        MT5Term[MT5 Terminal]
        Broker[Broker Servers]
        Market[Market Data]
    end

    CLI --> Main
    Config --> Main
    Main --> Engine
    Engine --> Scheduler

    Scheduler --> MH
    MH --> MA
    MA --> SD
    MA --> PA
    MA --> FIB
    MA --> RSI
    MA --> MV

    SD --> CS
    PA --> CS
    FIB --> CS
    RSI --> CS
    MV --> CS

    CS --> RM
    RM --> PS
    PS --> PC

    PC --> Order
    Order --> MT5
    MT5 --> MT5Term
    MT5Term --> Broker
    Broker --> Market

    Engine --> DB
    DB --> Repo
    Repo --> Models

    MT5 -.-> Mock
```

## 📊 Detailed End-to-End Trading Flow

### Phase 1: System Initialization

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Config
    participant Main
    participant DB
    participant MT5

    User->>CLI: uv run trading-bot start
    CLI->>Config: Load configuration
    Config-->>CLI: Trading parameters loaded
    CLI->>Main: Initialize TradingBot
    Main->>DB: Initialize database
    DB-->>Main: Database ready
    Main->>MT5: Connect to MT5 terminal
    MT5-->>Main: Connection established
    Main-->>CLI: System ready
    CLI-->>User: Bot started successfully
```

### Phase 2: Market Analysis Cycle

```mermaid
sequenceDiagram
    participant Scheduler
    participant MarketHours
    participant Analysis
    participant SupplyDemand
    participant PriceAction
    participant Fibonacci
    participant RSI
    participant MovingAverage
    participant Confluence

    Scheduler->>MarketHours: Check market status
    MarketHours-->>Scheduler: Market open

    Scheduler->>Analysis: Start analysis cycle
    Analysis->>SupplyDemand: Identify zones
    SupplyDemand-->>Analysis: Zones found (weight: 0.35)

    Analysis->>PriceAction: Analyze patterns
    PriceAction-->>Analysis: Patterns detected (weight: 0.15)

    Analysis->>Fibonacci: Check levels
    Fibonacci-->>Analysis: Key levels identified (weight: 0.12)

    Analysis->>RSI: Calculate RSI signals
    RSI-->>Analysis: RSI analysis complete (weight: 0.10)

    Analysis->>MovingAverage: Analyze MA trends
    MovingAverage-->>Analysis: MA analysis complete (weight: 0.08)

    Analysis->>Confluence: Calculate total score
    Confluence-->>Analysis: Score: 0.78 (>0.65 threshold)
    Analysis-->>Scheduler: Trading opportunity identified
```

### Phase 3: Risk Management & Position Sizing

```mermaid
sequenceDiagram
    participant Engine
    participant RiskMgmt
    participant PipCalc
    participant Account
    participant Position

    Engine->>RiskMgmt: Validate trade opportunity
    RiskMgmt->>Account: Get account balance
    Account-->>RiskMgmt: Balance: $10,000

    RiskMgmt->>PipCalc: Calculate position size
    Note over PipCalc: Symbol: EURUSD<br/>Entry: 1.0850<br/>Stop Loss: 1.0820<br/>Risk: 1.5%

    PipCalc->>PipCalc: Calculate pip distance (30 pips)
    PipCalc->>PipCalc: Calculate risk amount ($150)
    PipCalc->>PipCalc: Calculate volume (0.50 lots)
    PipCalc-->>RiskMgmt: Position size calculated

    RiskMgmt->>Position: Validate volume limits
    Position-->>RiskMgmt: Volume valid (min: 0.01, max: 100.0)
    RiskMgmt-->>Engine: Trade approved
```

### Phase 4: Order Execution

```mermaid
sequenceDiagram
    participant Engine
    participant OrderMgmt
    participant MT5Connector
    participant MT5Terminal
    participant Broker
    participant Database

    Engine->>OrderMgmt: Execute trade
    OrderMgmt->>MT5Connector: Send order

    Note over MT5Connector: Order Details:<br/>Symbol: EURUSD<br/>Type: BUY<br/>Volume: 0.50<br/>Entry: 1.0850<br/>SL: 1.0820<br/>TP: 1.0920

    MT5Connector->>MT5Terminal: place order
    MT5Terminal->>Broker: Submit to market
    Broker-->>MT5Terminal: Order filled
    MT5Terminal-->>MT5Connector: Execution confirmed

    Note over MT5Connector: Result:<br/>Ticket: 123456<br/>Fill Price: 1.0851<br/>Status: Success

    MT5Connector-->>OrderMgmt: Order executed
    OrderMgmt->>Database: Store trade record
    Database-->>OrderMgmt: Trade saved
    OrderMgmt-->>Engine: Trade complete
```

### Phase 5: Position Management

```mermaid
sequenceDiagram
    participant Monitor
    participant MT5Connector
    participant PositionMgmt
    participant RiskMgmt
    participant Database

    loop Every 5 seconds
        Monitor->>MT5Connector: Get position updates
        MT5Connector-->>Monitor: Current price: 1.0865

        Monitor->>PositionMgmt: Check position status
        PositionMgmt->>RiskMgmt: Evaluate risk levels

        alt Price hits breakeven
            RiskMgmt->>MT5Connector: Move SL to breakeven
            MT5Connector-->>RiskMgmt: SL updated
        else Price hits trailing stop
            RiskMgmt->>MT5Connector: Trail stop loss
            MT5Connector-->>RiskMgmt: SL trailed
        else Price hits take profit
            MT5Connector->>Monitor: Position closed
            Monitor->>Database: Update trade record
        end

        Monitor->>Database: Log position update
    end
```

## 🔄 Complete Trading Session Flow

```mermaid
graph TD
    Start([Start Trading Bot]) --> Init[Initialize System]
    Init --> CheckMarket{Market Open?}
    CheckMarket -->|No| Wait[Wait for Market]
    Wait --> CheckMarket
    CheckMarket -->|Yes| Analyze[Market Analysis]

    Analyze --> Foundation[Supply & Demand Analysis]
    Foundation --> Enhancement[Technical Indicators]
    Enhancement --> Score[Calculate Confluence Score]

    Score --> Threshold{Score > 65%?}
    Threshold -->|No| Wait2[Wait Next Cycle]
    Wait2 --> Analyze

    Threshold -->|Yes| Risk[Risk Management]
    Risk --> Size[Position Sizing]
    Size --> Validate{Valid Position?}
    Validate -->|No| Wait2

    Validate -->|Yes| Execute[Execute Trade]
    Execute --> Success{Order Success?}
    Success -->|No| Log[Log Error]
    Log --> Wait2

    Success -->|Yes| Monitor[Monitor Position]
    Monitor --> Update[Update Position]
    Update --> Closed{Position Closed?}
    Closed -->|No| Monitor

    Closed -->|Yes| Record[Record Results]
    Record --> Wait2

    Wait2 --> Stop{Stop Signal?}
    Stop -->|No| CheckMarket
    Stop -->|Yes| Shutdown[Shutdown System]
    Shutdown --> End([End])
```

## 📈 Trading Type Specific Flows

### Scalping Flow (M1-M15, High Frequency)

```mermaid
graph LR
    subgraph "Scalping Cycle (5s)"
        M1[M1 Analysis] --> M5[M5 Confluence]
        M5 --> M15[M15 Trend]
        M15 --> Quick[Quick Decision]
        Quick --> Entry[Fast Entry]
        Entry --> Monitor[Monitor 1-5min]
        Monitor --> Exit[Quick Exit]
    end
```

### Day Trading Flow (M15-H4, Balanced)

```mermaid
graph LR
    subgraph "Day Trading Cycle (30s)"
        M15[M15 Setup] --> H1[H1 Structure]
        H1 --> H4[H4 Trend]
        H4 --> Analysis[Detailed Analysis]
        Analysis --> Entry[Precise Entry]
        Entry --> Manage[Active Management]
        Manage --> Close[EOD Close]
    end
```

### Swing Trading Flow (H4-D1, Multi-day)

```mermaid
graph LR
    subgraph "Swing Trading Cycle (5min)"
        H4[H4 Setup] --> D1[D1 Structure]
        D1 --> W1[W1 Trend]
        W1 --> Patient[Patient Entry]
        Patient --> Hold[Hold Days]
        Hold --> Target[Target Levels]
    end
```

## 🏗️ Database Flow

```mermaid
erDiagram
    TradingSession ||--o{ Trade : contains
    Trade ||--o{ PositionUpdate : has
    Trade ||--|| MarketData : uses
    SystemHealth ||--o{ TradingSession : monitors

    TradingSession {
        int id PK
        datetime start_time
        datetime end_time
        string trading_type
        string status
        float total_pnl
        int total_trades
    }

    Trade {
        int id PK
        int session_id FK
        string symbol
        string asset_class
        string trading_type
        string trade_type
        float volume
        float entry_price
        float stop_loss
        float take_profit
        datetime opened_at
        datetime closed_at
        string status
        float realized_pnl
    }

    PositionUpdate {
        int id PK
        int trade_id FK
        string update_type
        string description
        float current_price
        float new_stop_loss
        float new_take_profit
        datetime updated_at
    }

    MarketData {
        int id PK
        string symbol
        float bid
        float ask
        float spread
        datetime timestamp
    }
```

## 🔧 Configuration Flow

```mermaid
graph TD
    Env[Environment Variables] --> Override[Config Override]
    Profile[Profile Config] --> Override
    Default[Default Config] --> Override

    Override --> Validate[Validation]
    Validate --> Error{Valid?}
    Error -->|No| Exit[Exit with Error]
    Error -->|Yes| Load[Load Trading Bot]

    Load --> Trading[Trading Parameters]
    Load --> Risk[Risk Parameters]
    Load --> Strategy[Strategy Parameters]
    Load --> MT5[MT5 Configuration]
    Load --> DB[Database Configuration]
```

## ⚡ Performance Metrics Flow

```mermaid
graph TD
    subgraph "Performance Tracking"
        Execution[Trade Execution] --> Latency[Latency Measurement]
        Latency --> Store[Store Metrics]

        Market[Market Analysis] --> Time[Analysis Time]
        Time --> Store

        Risk[Risk Calculation] --> Speed[Calculation Speed]
        Speed --> Store

        Store --> Health[Health Check]
        Health --> Alert{Performance OK?}
        Alert -->|No| Notify[Send Alert]
        Alert -->|Yes| Continue[Continue Trading]
    end
```

## 🚨 Error Handling Flow

```mermaid
graph TD
    Error[Error Detected] --> Type{Error Type}

    Type -->|Connection| Reconnect[Attempt Reconnection]
    Type -->|Market| Wait[Wait for Market]
    Type -->|Risk| Abort[Abort Trade]
    Type -->|System| Shutdown[Safe Shutdown]

    Reconnect --> Success1{Success?}
    Success1 -->|Yes| Resume[Resume Trading]
    Success1 -->|No| Retry{Retry Count?}
    Retry -->|< Max| Reconnect
    Retry -->|>= Max| Shutdown

    Wait --> Market[Check Market]
    Market --> Resume

    Abort --> Log[Log Error]
    Log --> Resume

    Shutdown --> Cleanup[Cleanup Resources]
    Cleanup --> Exit[Exit System]
```

## 📊 Key Trading Parameters

### Risk Management
- **Maximum risk per trade:** 0.2% - 1.8% (based on trading type)
- **Maximum daily loss:** 5%
- **Maximum drawdown:** 15%
- **Maximum open positions:** 3

### Position Sizing
- **Minimum volume:** 0.01 lots (all asset classes)
- **Maximum volume:** 100 lots (Forex), 50 lots (Commodities), 10 lots (Crypto)
- **Risk scaling:** Dynamic based on trading type and account balance

### Confluence Scoring
- **Minimum threshold:** 65%
- **Foundation weight:** 35% (Supply & Demand - mandatory)
- **Enhancement weights:** Price Action (15%), Fibonacci (12%), RSI (10%), MA (8%)

### Timing
- **Analysis frequency:** 5s (Scalping) → 5min (Swing)
- **Position monitoring:** Real-time
- **Database updates:** Every position change
- **Health checks:** Every 30 seconds

## 🎯 Trading Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> Connecting
    Connecting --> MarketCheck
    MarketCheck --> Analyzing : Market Open
    MarketCheck --> Waiting : Market Closed

    Analyzing --> OpportunityFound : Score > 65%
    Analyzing --> Waiting : Score < 65%

    OpportunityFound --> RiskCheck
    RiskCheck --> Executing : Valid
    RiskCheck --> Waiting : Invalid

    Executing --> Monitoring : Order Filled
    Executing --> Error : Order Failed

    Monitoring --> PositionUpdate : Price Change
    Monitoring --> Closing : Exit Signal
    PositionUpdate --> Monitoring

    Closing --> Recording : Position Closed
    Recording --> Waiting

    Waiting --> MarketCheck : Next Cycle
    Error --> Waiting : After Logging

    Waiting --> Shutdown : Stop Signal
    Analyzing --> Shutdown : Stop Signal
    Monitoring --> Shutdown : Stop Signal

    Shutdown --> [*]
```

This documentation provides a complete view of how the trading bot operates from start to finish, including all the technical analysis, risk management, and execution phases.