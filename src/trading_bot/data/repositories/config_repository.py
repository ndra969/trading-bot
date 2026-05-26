"""
Config Repository for Configuration Snapshots.

Provides CRUD operations for ConfigSnapshot model.
"""

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError

from ...utils.config_hasher import hash_config
from ...utils.logger import get_logger
from ..database import get_session
from ..models import ConfigSnapshot

logger = get_logger(__name__)


class ConfigRepository:
    """Repository for managing ConfigSnapshot database operations."""

    def __init__(self):
        """Initialize ConfigRepository."""
        self.logger = get_logger(self.__class__.__name__)

    async def create(
        self, config_data: dict, description: str | None = None, environment: str | None = None
    ) -> ConfigSnapshot:
        """
        Create a new config snapshot.

        Args:
            config_data: Configuration dictionary
            description: Optional description
            environment: Optional environment (development/production/backtest)

        Returns:
            Created ConfigSnapshot instance
        """
        # Generate hash
        config_hash = hash_config(config_data)

        async with get_session() as session:
            new_snapshot = ConfigSnapshot(
                config_hash=config_hash,
                config_json=config_data,
                description=description,
                environment=environment,
            )
            session.add(new_snapshot)

            try:
                await session.commit()
                await session.refresh(new_snapshot)
                self.logger.info(
                    f"Created config snapshot: {config_hash[:12]}... "
                    f"(env={environment or 'N/A'})"
                )
                return new_snapshot
            except IntegrityError:
                await session.rollback()
                self.logger.debug(f"Config snapshot already exists: {config_hash[:12]}...")
                # Return existing snapshot
                return await self.get_by_hash(config_hash)

    async def get_by_hash(self, config_hash: str) -> ConfigSnapshot | None:
        """
        Get config snapshot by hash.

        Args:
            config_hash: SHA256 hash

        Returns:
            ConfigSnapshot or None if not found
        """
        async with get_session() as session:
            stmt = select(ConfigSnapshot).where(ConfigSnapshot.config_hash == config_hash)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_or_create(
        self, config_data: dict, description: str | None = None, environment: str | None = None
    ) -> tuple[ConfigSnapshot, bool]:
        """
        Get existing config snapshot or create new one.

        Args:
            config_data: Configuration dictionary
            description: Optional description
            environment: Optional environment

        Returns:
            Tuple of (ConfigSnapshot, created_flag)
        """
        config_hash = hash_config(config_data)
        existing = await self.get_by_hash(config_hash)

        if existing:
            self.logger.debug(f"Config snapshot already exists: {config_hash[:12]}...")
            return existing, False

        new_snapshot = await self.create(config_data, description, environment)
        return new_snapshot, True

    async def list_recent(
        self, limit: int = 100, environment: str | None = None
    ) -> list[ConfigSnapshot]:
        """
        List recent config snapshots.

        Args:
            limit: Maximum number of snapshots to return
            environment: Optional environment filter

        Returns:
            List of ConfigSnapshot instances
        """
        async with get_session() as session:
            stmt = select(ConfigSnapshot).order_by(desc(ConfigSnapshot.created_at)).limit(limit)

            if environment:
                stmt = stmt.where(ConfigSnapshot.environment == environment)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def exists(self, config_hash: str) -> bool:
        """
        Check if config snapshot exists.

        Args:
            config_hash: SHA256 hash

        Returns:
            True if exists, False otherwise
        """
        snapshot = await self.get_by_hash(config_hash)
        return snapshot is not None

    async def delete(self, config_hash: str) -> bool:
        """
        Delete config snapshot.

        Args:
            config_hash: SHA256 hash

        Returns:
            True if deleted, False if not found
        """
        async with get_session() as session:
            stmt = select(ConfigSnapshot).where(ConfigSnapshot.config_hash == config_hash)
            result = await session.execute(stmt)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                return False

            try:
                await session.delete(snapshot)
                await session.commit()
                self.logger.info(f"Deleted config snapshot: {config_hash[:12]}...")
                return True
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error deleting config snapshot {config_hash[:12]}...: {e}")
                raise
