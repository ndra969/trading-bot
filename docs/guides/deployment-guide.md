# 🚀 Deployment Guide

## Deployment Overview

Complete guide for deploying trading bot from development to production environment with various deployment options.

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores, 2.4GHz
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: Stable internet connection (min 10Mbps)
- **OS**: Windows 10/11, Ubuntu 20.04+, macOS 10.15+

#### Recommended Requirements
- **CPU**: 4 cores, 3.0GHz+
- **RAM**: 8GB+
- **Storage**: 50GB SSD
- **Network**: Dedicated connection (100Mbps+)
- **OS**: Ubuntu 22.04 LTS (for production)

#### Software Dependencies
- **Python**: 3.11+
- **MetaTrader5**: Latest version
- **Git**: For version control
- **Docker**: For containerized deployment (optional)

## Local Development Setup

### 1. Environment Preparation

```bash
# Clone repository
git clone <repository-url>
cd bot-trading-2

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration Setup

```bash
# Copy environment template
cp .env.backup .env

# Create necessary directories
mkdir -p logs/csv
mkdir -p data
mkdir -p backups
```

### 3. Basic Configuration

Edit `.env` file with basic configuration:

```bash
# Broker Configuration
BROKER_NAME=YourBroker
BROKER_TYPE=broker_type
TRADING_SYMBOLS=EURUSD,GBPUSD,XAUUSD

# Risk Management
RISK_PER_TRADE=0.005
MAX_CONCURRENT_POSITIONS=5

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_TO_CONSOLE=true

# Telegram (Optional)
TELEGRAM_ENABLED=false
```

### 4. Database Initialization

```bash
# Initialize SQLite database
python -c "
from src.database.sqlite_manager import SQLiteManager
db = SQLiteManager()
db.initialize_database()
print('Database initialized successfully')
"
```

### 5. Test Run

```bash
# Test configuration
python -c "
from src.trading_bot import TradingBotV2
import os
from dotenv import load_dotenv

load_dotenv()
config = dict(os.environ)
bot = TradingBotV2(config)
print('Configuration loaded successfully')
"

# Run bot in test mode
python run_trading_bot.py
```

## Production Deployment

### Option 1: Direct Server Deployment

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Install system dependencies
sudo apt install git curl wget build-essential -y

# Create trading user
sudo useradd -m -s /bin/bash trading
sudo usermod -aG sudo trading
```

#### 2. Application Setup

```bash
# Switch to trading user
sudo su - trading

# Clone repository
git clone <repository-url> /home/trading/bot-trading-2
cd /home/trading/bot-trading-2

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Production Configuration

```bash
# Copy production environment
cp .env.backup .env

# Edit production configuration
nano .env
```

Production `.env` configuration:
```bash
# Production Environment
APP_ENVIRONMENT=production
LOG_LEVEL=WARN
LOG_TO_CONSOLE=false
LOG_TO_FILE=true

# Enhanced Security
TELEGRAM_USE_LENIENT_SSL=false
TELEGRAM_SSL_VERIFY=true

# Performance Optimization
TRADING_LOOP_INTERVAL_SECONDS=60
MAX_LOOP_EXECUTION_TIME=50
ASYNC_TIMEOUT_SECONDS=30

# Database Optimization
CSV_LOGGING_ENABLED=false  # Use SQLite only in production
CSV_COMPRESSION_ENABLED=true

# Monitoring
MONITOR_SYSTEM_PERFORMANCE=true
MEMORY_ALERT_THRESHOLD_PERCENT=80
CPU_ALERT_THRESHOLD_PERCENT=80
```

#### 4. Systemd Service Setup

Create systemd service file:
```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Service configuration:
```ini
[Unit]
Description=Trading Bot Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory=/home/trading/bot-trading-2
Environment=PATH=/home/trading/bot-trading-2/venv/bin
ExecStart=/home/trading/bot-trading-2/venv/bin/python run_trading_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-bot

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/trading/bot-trading-2

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable trading-bot

# Start service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot
```

### Option 2: Docker Deployment

#### 1. Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run_trading_bot.py .
COPY .env.production .env

# Create necessary directories
RUN mkdir -p logs/csv data backups

# Create non-root user
RUN useradd -m -u 1000 trading && chown -R trading:trading /app
USER trading

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose port for monitoring
EXPOSE 8000

# Run application
CMD ["python", "run_trading_bot.py"]
```

#### 2. Docker Compose

```yaml
version: '3.8'

services:
  trading-bot:
    build: .
    container_name: trading-bot
    restart: unless-stopped
    environment:
      - APP_ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
      - ./config:/app/config
    networks:
      - trading-network
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s

  # Optional: Monitoring stack
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - trading-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    networks:
      - trading-network

networks:
  trading-network:
    driver: bridge

volumes:
  grafana-storage:
```

#### 3. Docker Deployment Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f trading-bot

# Stop services
docker-compose down

# Update and restart
docker-compose pull
docker-compose up -d --force-recreate
```

### Option 3: Cloud Deployment (AWS)

#### 1. EC2 Instance Setup

```bash
# Launch EC2 instance (t3.medium recommended)
# Ubuntu 22.04 LTS AMI
# Security group: SSH (22), Custom (8000 for monitoring)

# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Application Deployment

```bash
# Clone repository
git clone <repository-url>
cd bot-trading-2

# Setup environment
cp .env.backup .env.production
nano .env.production

# Deploy with Docker
docker-compose -f docker-compose.prod.yml up -d
```

#### 3. AWS-Specific Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  trading-bot:
    build: .
    restart: unless-stopped
    environment:
      - APP_ENVIRONMENT=production
      - AWS_REGION=us-east-1
    volumes:
      - /opt/trading-bot/data:/app/data
      - /opt/trading-bot/logs:/app/logs
    logging:
      driver: awslogs
      options:
        awslogs-group: trading-bot
        awslogs-region: us-east-1
        awslogs-stream-prefix: trading-bot
```

## Monitoring & Maintenance

### 1. Log Management

#### Log Rotation Setup
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/trading-bot
```

```bash
/home/trading/bot-trading-2/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 trading trading
    postrotate
        systemctl reload trading-bot
    endscript
}
```

#### Log Monitoring
```bash
# Real-time log monitoring
tail -f /home/trading/bot-trading-2/logs/trading_bot.log

# Search for errors
grep -i error /home/trading/bot-trading-2/logs/trading_bot.log

# Monitor system logs
journalctl -u trading-bot -f
```

### 2. Performance Monitoring

#### System Monitoring Script
```bash
#!/bin/bash
# monitor.sh

# Check service status
if ! systemctl is-active --quiet trading-bot; then
    echo "Trading bot service is not running!"
    systemctl restart trading-bot
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')
if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "High memory usage: $MEMORY_USAGE%"
fi

# Check disk space
DISK_USAGE=$(df /home/trading | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "High disk usage: $DISK_USAGE%"
fi

# Check log file size
LOG_SIZE=$(du -m /home/trading/bot-trading-2/logs/trading_bot.log | cut -f1)
if [ $LOG_SIZE -gt 100 ]; then
    echo "Large log file: ${LOG_SIZE}MB"
fi
```

#### Cron Job Setup
```bash
# Add monitoring cron job
crontab -e

# Add this line for 5-minute monitoring
*/5 * * * * /home/trading/monitor.sh >> /home/trading/monitor.log 2>&1
```

### 3. Backup Strategy

#### Database Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/trading/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="/home/trading/bot-trading-2/data/trading_bot.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp $DB_FILE "$BACKUP_DIR/trading_bot_$DATE.db"

# Compress backup
gzip "$BACKUP_DIR/trading_bot_$DATE.db"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "trading_bot_*.db.gz" -mtime +30 -delete

echo "Backup completed: trading_bot_$DATE.db.gz"
```

#### Automated Backup
```bash
# Add backup cron job
crontab -e

# Daily backup at 2 AM
0 2 * * * /home/trading/backup.sh >> /home/trading/backup.log 2>&1
```

## Security Considerations

### 1. System Security

```bash
# Update system regularly
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000  # For monitoring (if needed)

# Disable root login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart ssh
```

### 2. Application Security

```bash
# Secure file permissions
chmod 600 .env
chmod 700 logs/
chmod 700 data/
chmod 700 backups/

# Secure database file
chmod 600 data/trading_bot.db
```

### 3. Network Security

```bash
# Use VPN for MT5 connection (recommended)
# Configure SSL/TLS for all external communications
# Use secure Telegram bot tokens
# Implement IP whitelisting if possible
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check service status
sudo systemctl status trading-bot

# Check logs
journalctl -u trading-bot -n 50

# Check configuration
python -c "from dotenv import load_dotenv; load_dotenv(); print('Config OK')"
```

#### 2. High Memory Usage
```bash
# Monitor memory
htop

# Check for memory leaks
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Restart service if needed
sudo systemctl restart trading-bot
```

#### 3. Database Issues
```bash
# Check database integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# Backup and repair if needed
cp data/trading_bot.db data/trading_bot.db.backup
sqlite3 data/trading_bot.db ".recover" | sqlite3 data/trading_bot_recovered.db
```

### Performance Optimization

#### 1. System Optimization
```bash
# Increase file limits
echo "trading soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "trading hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### 2. Application Optimization
```bash
# Use production configuration
APP_ENVIRONMENT=production
LOG_LEVEL=WARN
CSV_LOGGING_ENABLED=false

# Optimize database
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

## Deployment Checklist

### Pre-Deployment
- [ ] System requirements met
- [ ] Dependencies installed
- [ ] Configuration files prepared
- [ ] Database initialized
- [ ] Backup strategy implemented
- [ ] Monitoring setup configured

### Deployment
- [ ] Application deployed
- [ ] Service configured and started
- [ ] Logs are being generated
- [ ] Database is accessible
- [ ] Telegram notifications working (if enabled)
- [ ] Performance monitoring active

### Post-Deployment
- [ ] System monitoring active
- [ ] Backup jobs scheduled
- [ ] Log rotation configured
- [ ] Security measures implemented
- [ ] Documentation updated
- [ ] Team notified of deployment

This comprehensive deployment guide ensures a smooth transition from development to production environment with proper monitoring and maintenance procedures.
