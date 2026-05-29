"""
Command-Line Interface

Click-based CLI for managing the trading bot.
"""

import sys

import click
from rich.console import Console
from rich.table import Table
from trading_core.config import Configuration
from trading_core.data.database import init_database
from trading_core.utils.logger import get_logger, setup_logger

from .connectors.account_manager import AccountManager
from .connectors.mt5_connector import MT5Connector

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

    # If --dry-run not passed on CLI, fall back to config (e.g. test.yaml sets it).
    # Without this, --config test (dry_run: true) was silently overridden to live mode
    # because the CLI flag defaulted to False.
    if not dry_run:
        dry_run = bool(config.get("trading", {}).get("dry_run", False))
        if dry_run:
            console.print("[yellow]DRY-RUN: enabled from config (trading.dry_run)[/yellow]")

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

                # Log MT5 config for debugging (without sensitive data)
                logger.debug(
                    f"MT5 Config: login={'***' if mt5_config.login else None}, "
                    f"server={mt5_config.server or 'None (will use existing MT5 connection)'}, "
                    f"terminal_path={mt5_config.terminal_path or 'Auto-detect'}"
                )

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
                "analysis_interval": config.get("analysis_interval", 60),
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


@cli.command(name="verify-data")
@click.option("--limit", default=20, help="Number of recent closed positions to verify")
@click.option("--symbol", default=None, help="Filter by symbol (e.g., EURUSD)")
@click.pass_context
def verify_data(ctx, limit, symbol):
    """Cross-check recent CLOSED positions in DB against MT5 deal history.

    For each position, fetches the MT5 deal by ticket and compares:
    - close_price (DB vs MT5)
    - realized P&L (DB vs MT5)
    - MT5 deal.reason matches DB close_reason

    Discrepancies are shown in a table. Empty table = data is accurate.
    """
    import asyncio

    asyncio.run(_run_verify_data(ctx, limit, symbol))


async def _run_verify_data(ctx, limit, symbol):
    from sqlalchemy import desc, select
    from trading_core.data.database import get_session, init_database
    from trading_core.data.models import Position as DBPosition
    from trading_core.enums.close_reason import (
        resolve_close_reason,
    )

    config = ctx.obj["config"]
    init_database(config.database.url)

    global _mt5_connector
    if not _mt5_connector or not _mt5_connector.is_connected():
        console.print("[red]MT5 not connected.[/red] Run 'mt5 connect' first.")
        return

    async with get_session() as session:
        stmt = (
            select(DBPosition)
            .where(DBPosition.status == "CLOSED", DBPosition.ticket.isnot(None))
            .order_by(desc(DBPosition.close_time))
            .limit(limit)
        )
        if symbol:
            stmt = stmt.where(DBPosition.symbol == symbol)
        result = await session.execute(stmt)
        positions = list(result.scalars().all())

    if not positions:
        console.print("[yellow]No CLOSED positions with tickets found.[/yellow]")
        return

    table = Table(title=f"Verify {len(positions)} positions vs MT5 history")
    table.add_column("Ticket", style="cyan")
    table.add_column("Symbol", style="cyan")
    table.add_column("DB Close", style="white")
    table.add_column("MT5 Close", style="white")
    table.add_column("Δ pips", style="yellow")
    table.add_column("DB P&L", style="white")
    table.add_column("MT5 P&L", style="white")
    table.add_column("DB Reason", style="white")
    table.add_column("Expected", style="green")

    mismatches = 0
    for p in positions:
        deal = _mt5_connector.get_history_deal(p.ticket)
        if not deal:
            table.add_row(
                str(p.ticket),
                p.symbol,
                f"{p.close_price:.5f}",
                "[red]N/A[/red]",
                "-",
                f"${p.current_pnl_usd:.2f}",
                "-",
                p.close_reason or "NULL",
                "-",
            )
            mismatches += 1
            continue

        mt5_price = deal.get("price", 0)
        mt5_pnl = deal.get("profit", 0.0) + deal.get("swap", 0.0) + deal.get("commission", 0.0)
        mt5_reason_code = deal.get("reason")
        expected_reason = resolve_close_reason(_db_pos_as_position(p), mt5_reason_code).value

        pip_diff = abs((p.close_price or 0) - mt5_price) / (p.pip_size or 0.0001)
        reason_match = p.close_reason == expected_reason

        style = (
            ""
            if (pip_diff < 1 and abs(mt5_pnl - p.current_pnl_usd) < 0.5 and reason_match)
            else "red"
        )
        if style == "red":
            mismatches += 1

        table.add_row(
            f"[{style}]{p.ticket}[/{style}]" if style else str(p.ticket),
            p.symbol,
            f"{p.close_price:.5f}" if p.close_price else "NULL",
            f"{mt5_price:.5f}",
            f"{pip_diff:.1f}",
            f"${p.current_pnl_usd:.2f}",
            f"${mt5_pnl:.2f}",
            p.close_reason or "NULL",
            expected_reason,
        )

    console.print(table)
    if mismatches > 0:
        console.print(f"[red]⚠ {mismatches} discrepancies found[/red]")
    else:
        console.print(f"[green]✓ All {len(positions)} positions match MT5 history[/green]")


def _db_pos_as_position(db_pos):
    """Light shim so resolve_close_reason can read .breakeven_activated / .trailing_activated."""
    from types import SimpleNamespace

    return SimpleNamespace(
        breakeven_activated=db_pos.breakeven_activated,
        trailing_activated=db_pos.trailing_activated,
    )


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

    # Trading-specific knobs now live per-symbol / per-asset-class
    # (see active_symbols.yaml and strategy_parameters.yaml).

    # Logging
    table.add_row("logging.level", config.logging.level)
    table.add_row("logging.file_path", config.logging.file_path)

    console.print(table)


@cli.command()
def version():
    """Show version information"""
    from . import __version__

    console.print(f"[bold cyan]Trading Bot v{__version__}[/bold cyan]")


def _display_claude_rules(format: str):
    """Helper function to display CLAUDE.md rules"""
    import sys
    from pathlib import Path

    # Fix Windows console encoding for Unicode characters
    if sys.platform == "win32":
        try:
            # Try to set UTF-8 encoding for Windows console
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # Ignore if reconfiguration fails

    # CLAUDE.md lives at the repo root; resolve relative to the working
    # directory (run from repo root), robust to monorepo package nesting.
    claude_md_path = Path("CLAUDE.md")

    if not claude_md_path.exists():
        console.print("[bold red]Error:[/bold red] CLAUDE.md not found!")
        return

    try:
        with open(claude_md_path, encoding="utf-8") as f:
            content = f.read()

        if format == "summary":
            # Extract key sections
            console.print("[bold cyan]Trading Bot Project Rules - Summary[/bold cyan]\n")
            console.print("[bold yellow]Quick Reference:[/bold yellow]\n")

            # Extract key rules
            sections = {
                "Critical Implementation Rules": content.find("## Critical Implementation Rules"),
                "Code Quality Standards": content.find("## Code Quality Standards"),
                "Testing Requirements": content.find("## Testing Requirements"),
                "TDD Workflow": content.find("## Test-Driven Development"),
            }

            for section_name, pos in sections.items():
                if pos != -1:
                    end_pos = content.find("\n## ", pos + 1)
                    if end_pos == -1:
                        end_pos = len(content)
                    section_content = content[pos:end_pos]
                    # Show first 500 chars of each section, clean up markdown
                    preview = section_content[:500].replace("#", "").strip()
                    # Remove problematic Unicode characters for Windows console
                    preview = preview.encode("ascii", "ignore").decode("ascii")
                    console.print(f"[bold green]{section_name}[/bold green]")
                    console.print(preview + "...\n")

        elif format == "rules-only":
            # Extract only critical rules
            console.print("[bold cyan]Critical Project Rules[/bold cyan]\n")
            rules_start = content.find("## Critical Implementation Rules")
            if rules_start != -1:
                rules_end = content.find("\n## ", rules_start + 1)
                if rules_end == -1:
                    rules_end = len(content)
                rules_section = content[rules_start:rules_end]
                # Use print() directly for better Windows compatibility
                print(rules_section)
            else:
                console.print("[yellow]Critical rules section not found[/yellow]")

        else:  # full
            console.print("[bold cyan]Complete Project Rules & Guidelines[/bold cyan]\n")
            # Use print() directly for full content to avoid encoding issues
            print(content)

        console.print(
            "\n[dim]Tip: Use 'trading-bot rules --format summary' for quick reference[/dim]"
        )
        console.print(
            "[dim]Tip: Use 'trading-bot rules --format rules-only' for critical rules only[/dim]"
        )
        console.print(
            "[dim]Tip: Use 'trading-bot claude' as an alias for 'trading-bot rules'[/dim]"
        )

    except Exception as e:
        # Use print() for error messages to avoid encoding issues
        print(f"Error reading CLAUDE.md: {e}", file=sys.stderr)


@cli.command()
@click.option(
    "--format",
    type=click.Choice(["full", "summary", "rules-only"], case_sensitive=False),
    default="full",
    help="Display format: full (complete guide), summary (key points), rules-only (critical rules only)",
)
def rules(format):
    """Display project rules and guidelines from CLAUDE.md"""
    _display_claude_rules(format)


@cli.command()
@click.option(
    "--format",
    type=click.Choice(["full", "summary", "rules-only"], case_sensitive=False),
    default="full",
    help="Display format: full (complete guide), summary (key points), rules-only (critical rules only)",
)
def claude(format):
    """Display project rules and guidelines from CLAUDE.md (alias for 'rules' command)"""
    _display_claude_rules(format)


if __name__ == "__main__":
    cli()
