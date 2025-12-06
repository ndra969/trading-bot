"""
Command-Line Interface

Click-based CLI for managing the trading bot.
"""

import sys

import click
from rich.console import Console
from rich.table import Table

from .config import Configuration
from .connectors.account_manager import AccountManager
from .connectors.mt5_connector import MT5Connector
from .data.database import init_database
from .utils.logger import get_logger, setup_logger

console = Console()
logger = None
_mt5_connector = None  # Global MT5 connector instance
_dry_run_mode = False  # Global dry-run flag


@click.group()
@click.option(
    "--config",
    default="development",
    help="Configuration environment (development, production, test)",
)
@click.pass_context
def cli(ctx, config):
    """Trading Bot - Modern Python Trading System"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Configuration(env=config)

    # Setup logger
    log_config = ctx.obj["config"].logging
    setup_logger(
        log_file=log_config.file_path,
        level=log_config.level,
        rotation=log_config.max_file_size,
        retention=log_config.backup_count,
    )

    global logger
    logger = get_logger(__name__)
    logger.info(f"CLI initialized with config: {config}")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Run in dry-run mode (mock MT5, no real trades)")
@click.option(
    "--connect-mt5",
    is_flag=True,
    help="Connect to real MT5 in dry-run mode (for testing with real data)",
)
@click.pass_context
def start(ctx, dry_run, connect_mt5):
    """Start the trading bot"""
    global _dry_run_mode
    config = ctx.obj["config"]

    console.print("[bold green]Starting Trading Bot...[/bold green]")

    # Determine MT5 mode based on flags
    use_mock_mt5 = False
    if dry_run:
        _dry_run_mode = True
        if connect_mt5:
            # Dry-run with real MT5 connection (simulate orders only)
            console.print("[yellow]DRY-RUN: Real MT5 connection, simulated orders[/yellow]")
        else:
            # Dry-run with mock MT5 (complete simulation)
            use_mock_mt5 = True
            console.print("[yellow]DRY-RUN: Mock MT5, fully simulated (safe mode)[/yellow]")
    elif connect_mt5:
        # --connect-mt5 without --dry-run is ignored
        console.print("[yellow]WARNING: --connect-mt5 ignored (only valid with --dry-run)[/yellow]")

    try:
        # Validate configuration
        config.validate()
        console.print("[green]OK[/green] Configuration validated")

        # Initialize database
        db_url = config.database.url
        db_manager = init_database(db_url, echo=config.database.echo)

        # Create tables if they don't exist
        import asyncio

        async def create_tables():
            await db_manager.create_tables()

        asyncio.run(create_tables())

        # Extract database name for display (security)
        db_name = (
            db_url.split("///")[-1].split("/")[-1].split("?")[0]
            if "sqlite" in db_url
            else db_url.split("/")[-1].split("?")[0]
        )
        db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
        console.print(f"[green]OK[/green] Database initialized: {db_type} ({db_name})")

        # Initialize MT5 connection
        global _mt5_connector

        if use_mock_mt5:
            # Use mock MT5 connector (dry-run default)
            console.print("\n[cyan]Initializing MOCK MT5 (Safe Mode)...[/cyan]")

            # In mock mode, skip MT5 connection entirely
            console.print(
                "[green]OK[/green] MOCK MT5 - Account: 12345678 (SIMULATED) | Balance: $10,000.00"
            )
            console.print("[cyan]   > All data is simulated (no real MT5 required)[/cyan]")
            logger.info("Using MOCK MT5 connector - Safe dry-run mode")
            _mt5_connector = None  # Mock mode doesn't use real connector

        if not use_mock_mt5:
            # Use real MT5 connection
            console.print("\n[cyan]Connecting to MT5...[/cyan]")

            try:
                mt5_config = config.mt5
                _mt5_connector = MT5Connector(
                    terminal_path=mt5_config.terminal_path,
                    login=mt5_config.login,
                    password=mt5_config.password,
                    server=mt5_config.server,
                    timeout=mt5_config.connection_timeout,
                    retry_attempts=mt5_config.retry_attempts,
                )

                if _mt5_connector.initialize():
                    account_info = _mt5_connector.account_info

                    if dry_run:
                        console.print(
                            f"[green]OK[/green] MT5 connected (DRY-RUN) - Account: {account_info.get('login', 'N/A')} | Balance: ${account_info.get('balance', 0):,.2f}"
                        )
                        console.print(
                            "[yellow]   Orders will be SIMULATED (no real execution)[/yellow]"
                        )
                    else:
                        console.print(
                            f"[green]OK[/green] MT5 connected - Account: {account_info.get('login', 'N/A')} | Balance: ${account_info.get('balance', 0):,.2f}"
                        )

                    logger.info(
                        f"MT5 connected - Account: {account_info.get('login')} - Dry-run: {dry_run}"
                    )
                else:
                    console.print(
                        "[yellow]WARNING: MT5 connection failed (will continue without MT5)[/yellow]"
                    )
                    logger.warning("Failed to connect to MT5")
                    _mt5_connector = None

            except ImportError:
                console.print("[yellow]WARNING: MetaTrader5 not available (Windows only)[/yellow]")
                _mt5_connector = None
            except Exception as e:
                console.print(
                    f"[yellow]WARNING: MT5 error: {e} (will continue without MT5)[/yellow]"
                )
                logger.warning(f"MT5 connection error: {e}")
                _mt5_connector = None

        console.print("\n[bold green]Trading Bot started successfully![/bold green]")
        console.print("\nPress Ctrl+C to stop...")

        # Start TradingBot with main loop
        try:
            from .main import TradingBot

            # Create bot instance
            bot_config = {
                "env": config.env,  # Pass environment name
                "symbols": config.get("symbols", ["EURUSD", "GBPUSD"]),
                "timeframe": config.get("timeframe", "H1"),
                "analysis_interval": config.get("analysis_interval", 300),
                "trading": {
                    "dry_run": dry_run,  # Pass CLI dry-run flag
                },
                "initial_balance": config.get(
                    "initial_balance", 10000.0
                ),  # Ensure this is passed if needed
                "risk_management": config.get("risk_management", {}),  # Pass risk config
                "position_manager": config.get("position_manager", {}),  # Pass position config
            }

            # Update bot_config with full config object content for other settings
            # This is a bit of a hack to ensure the bot has access to all settings
            # A better approach would be to pass the full Configuration object
            if hasattr(config, "_config"):
                bot_config.update(config._config)

            # Explicitly set dry_run from CLI to override file config
            if "trading" not in bot_config:
                bot_config["trading"] = {}
            bot_config["trading"]["dry_run"] = dry_run

            bot = TradingBot(bot_config)

            # Override MT5 connector if available
            if _mt5_connector:
                bot.mt5 = _mt5_connector
                from .connectors.data_manager import DataManager
                from .connectors.symbol_manager import SymbolManager

                symbol_manager = SymbolManager(_mt5_connector)
                bot.data_manager = DataManager(_mt5_connector, symbol_manager)

            # Start bot (this will run the trading loop)
            import asyncio

            logger.info("Starting TradingBot main loop...")
            asyncio.run(bot.start())

        except KeyboardInterrupt:
            logger.info("Received stop signal (Ctrl+C)")
            console.print("\n[yellow]Stopping bot...[/yellow]")
            if bot:
                asyncio.run(bot.stop())
        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)
            console.print(f"[red]ERROR: {e}[/red]")
            raise

    except Exception as e:
        console.print(f"[bold red]ERROR: Error starting bot: {e}[/bold red]")
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop the trading bot"""
    global _mt5_connector

    console.print("[bold yellow]Stopping Trading Bot...[/bold yellow]")

    # Disconnect MT5 if connected
    if _mt5_connector:
        try:
            _mt5_connector.shutdown()
            console.print("[green]OK[/green] MT5 disconnected")
            logger.info("MT5 disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting MT5: {e}")
        _mt5_connector = None

    logger.info("Trading bot stopped")
    console.print("[bold green]Trading Bot stopped successfully![/bold green]")


@cli.command()
@click.pass_context
def status(ctx):
    """Show trading bot status"""
    config = ctx.obj["config"]

    table = Table(title="Trading Bot Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    # Extract database name for display (security)
    db_url = config.database.url
    db_name = (
        db_url.split("///")[-1].split("/")[-1].split("?")[0]
        if "sqlite" in db_url
        else db_url.split("/")[-1].split("?")[0]
    )
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"

    # Check MT5 connection status
    global _mt5_connector
    if _mt5_connector and _mt5_connector.is_connected():
        mt5_status = "[green]OK[/green] Connected"
        mt5_details = f"Account: {_mt5_connector.account_info.get('login', 'N/A')}"
    else:
        mt5_status = "[yellow]WARN[/yellow] Not Connected"
        mt5_details = "Use 'mt5 connect' command"

    table.add_row("Configuration", "[green]OK[/green] Loaded", config.env)
    table.add_row("Database", "[green]OK[/green] Ready", f"{db_type} ({db_name})")
    table.add_row("Logging", "[green]OK[/green] Active", config.logging.level)
    table.add_row("MT5", mt5_status, mt5_details)

    console.print(table)


@cli.group()
def mt5():
    """MetaTrader5 commands"""
    pass


@mt5.command()
@click.option("--terminal-path", help="MT5 terminal path")
@click.option("--login", type=int, help="MT5 login")
@click.option("--password", help="MT5 password")
@click.option("--server", help="MT5 server")
@click.pass_context
def connect(ctx, terminal_path, login, password, server):
    """Connect to MetaTrader5"""
    global _mt5_connector

    config = ctx.obj["config"]
    console.print("[bold green]Connecting to MT5...[/bold green]")

    try:
        # Get credentials from options or config/env
        mt5_config = config.mt5
        terminal = terminal_path or mt5_config.terminal_path
        login_id = login or mt5_config.login
        pwd = password or mt5_config.password
        srv = server or mt5_config.server

        # Create connector
        _mt5_connector = MT5Connector(
            terminal_path=terminal,
            login=login_id,
            password=pwd,
            server=srv,
            timeout=mt5_config.connection_timeout,
            retry_attempts=mt5_config.retry_attempts,
        )

        # Initialize connection
        if _mt5_connector.initialize():
            # Get account info
            account_info = _mt5_connector.account_info

            console.print("[green]SUCCESS: Connected to MT5 successfully![/green]")
            console.print("\n[cyan]Account Information:[/cyan]")
            console.print(f"  Login: {account_info.get('login', 'N/A')}")
            console.print(f"  Server: {account_info.get('server', 'N/A')}")
            console.print(f"  Company: {account_info.get('company', 'N/A')}")
            console.print(f"  Balance: ${account_info.get('balance', 0):,.2f}")
            console.print(f"  Equity: ${account_info.get('equity', 0):,.2f}")
            console.print(f"  Leverage: 1:{account_info.get('leverage', 1)}")

            logger.info("MT5 connection established successfully")
        else:
            console.print("[red]ERROR: Failed to connect to MT5[/red]")
            logger.error("MT5 connection failed")
            _mt5_connector = None

    except ImportError:
        console.print("[red]ERROR: MetaTrader5 package not installed[/red]")
        console.print("  Install with: pip install MetaTrader5")
        console.print("  Note: MT5 only works on Windows")
    except Exception as e:
        console.print(f"[red]ERROR: Connection error: {e}[/red]")
        logger.error(f"MT5 connection error: {e}")
        _mt5_connector = None


@mt5.command()
@click.pass_context
def disconnect(ctx):
    """Disconnect from MetaTrader5"""
    global _mt5_connector

    console.print("[bold yellow]Disconnecting from MT5...[/bold yellow]")

    if _mt5_connector:
        try:
            _mt5_connector.shutdown()
            _mt5_connector = None
            console.print("[green]SUCCESS: Disconnected successfully[/green]")
            logger.info("MT5 disconnected")
        except Exception as e:
            console.print(f"[yellow]Warning: {e}[/yellow]")
    else:
        console.print("[yellow]No active connection[/yellow]")


@mt5.command(name="status")
@click.pass_context
def mt5_status(ctx):
    """Show MT5 connection status"""
    global _mt5_connector

    console.print("[bold cyan]MT5 Connection Status[/bold cyan]\n")

    if _mt5_connector and _mt5_connector.is_connected():
        console.print("[green]Status: Connected[/green]\n")

        # Get terminal info
        terminal_info = _mt5_connector.terminal_info
        account_info = _mt5_connector.account_info

        table = Table(title="Connection Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Terminal", terminal_info.get("name", "Unknown"))
        table.add_row("Account", str(account_info.get("login", "N/A")))
        table.add_row("Server", account_info.get("server", "N/A"))
        table.add_row("Company", account_info.get("company", "N/A"))
        table.add_row("Balance", f"${account_info.get('balance', 0):,.2f}")
        table.add_row("Equity", f"${account_info.get('equity', 0):,.2f}")
        table.add_row("Trade Allowed", "Yes" if terminal_info.get("trade_allowed") else "No")

        console.print(table)
    else:
        console.print("[yellow]Status: Not Connected[/yellow]")
        console.print("\nUse 'trading-bot mt5 connect' to establish connection")


@cli.group()
def account():
    """Account management commands"""
    pass


@account.command()
@click.pass_context
def info(ctx):
    """Show account information"""
    global _mt5_connector

    console.print("[bold cyan]Account Information[/bold cyan]\n")

    if not _mt5_connector or not _mt5_connector.is_connected():
        console.print("[yellow]MT5 not connected[/yellow]")
        console.print("Use 'trading-bot mt5 connect' first")
        return

    try:
        # Get account manager
        account_manager = AccountManager(_mt5_connector)
        summary = account_manager.get_summary()

        # Create info table
        table = Table(title="Account Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Balance", f"${summary['balance']:,.2f}")
        table.add_row("Equity", f"${summary['equity']:,.2f}")
        table.add_row("Margin", f"${summary['margin']:,.2f}")
        table.add_row("Free Margin", f"${summary['free_margin']:,.2f}")
        table.add_row("Margin Level", f"{summary['margin_level']:.2f}%")
        table.add_row("Profit", f"${summary['profit']:,.2f}")
        table.add_row("Leverage", f"1:{summary['leverage']}")
        table.add_row("Currency", summary["currency"])
        table.add_row("Server", summary["server"])
        table.add_row("Company", summary["company"])
        table.add_row("Account Type", summary["account_type"])
        table.add_row("Trade Allowed", "Yes" if summary["trade_allowed"] else "No")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Failed to get account info: {e}")


@cli.group(name="config")
def config_group():
    """Configuration management commands"""
    pass


@config_group.command()
@click.pass_context
def validate(ctx):
    """Validate configuration"""
    config = ctx.obj["config"]

    try:
        config.validate()
        console.print("[bold green]OK: Configuration is valid![/bold green]")

        table = Table(title="Configuration Summary")
        table.add_column("Section", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Database", "Valid")
        table.add_row("Trading", "Valid")
        table.add_row("Logging", "Valid")
        table.add_row("Telegram", "Valid")
        table.add_row("MT5", "Valid")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]ERROR: Configuration validation failed: {e}[/bold red]")
        sys.exit(1)


@config_group.command()
@click.pass_context
def show(ctx):
    """Show current configuration"""
    config = ctx.obj["config"]

    table = Table(title=f"Configuration ({config.env})")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="yellow")

    # Database (hide credentials)
    db_url = config.database.url
    db_name = (
        db_url.split("///")[-1].split("/")[-1].split("?")[0]
        if "sqlite" in db_url
        else db_url.split("/")[-1].split("?")[0]
    )
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
    table.add_row("database.type", db_type)
    table.add_row("database.name", db_name)
    table.add_row("database.pool_size", str(config.database.pool_size))

    # Trading
    table.add_row("trading.risk_per_trade", str(config.trading.risk_per_trade))
    table.add_row("trading.max_concurrent_positions", str(config.trading.max_concurrent_positions))

    # Logging
    table.add_row("logging.level", config.logging.level)
    table.add_row("logging.file_path", config.logging.file_path)

    console.print(table)


@cli.command()
def version():
    """Show version information"""
    from . import __version__

    console.print(f"[bold cyan]Trading Bot v{__version__}[/bold cyan]")


if __name__ == "__main__":
    cli()
