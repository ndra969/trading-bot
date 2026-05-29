"""Zone Manager - Manages zone lifecycle and storage."""

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import select
from trading_core.data import SupplyDemandZone, get_session
from trading_core.utils.logger import get_logger

from trading_worker.strategies.foundation.zone_detector import DetectedZone, ZoneType

logger = get_logger(__name__)


class ZoneManager:
    """Manages detected zones lifecycle and storage."""

    def __init__(self, config: dict[str, Any] | None = None, use_database: bool = True):
        """
        Initialize zone manager.

        Args:
            config: Configuration with max_zones_per_symbol, max_zone_age_hours, etc.
            use_database: Whether to persist zones to database
        """
        self.config = config or {}
        self.zones: dict[str, list[DetectedZone]] = {}
        self.max_zones_per_symbol = self.config.get("max_zones_per_symbol", 50)
        self.max_zone_age_hours = self.config.get("max_zone_age_hours", 72)
        self.use_database = use_database
        self._zone_id_map: dict[str, int] = {}  # Map zone_id to database id
        self._db_lock = asyncio.Lock()  # Global lock for all database operations
        self._symbol_locks: dict[str, asyncio.Lock] = {}  # Per-symbol locks
        logger.info(f"ZoneManager initialized (database: {use_database})")

    async def add_zones(
        self, symbol: str, zones: list[DetectedZone], timeframe: str = "H1"
    ) -> None:
        """
        Add detected zones for a symbol with deduplication and update logic.

        Args:
            symbol: Trading symbol
            zones: Newly detected zones
            timeframe: Timeframe for zones
        """
        if symbol not in self.zones:
            self.zones[symbol] = []

        # Use global lock to prevent any concurrent database operations
        async with self._db_lock:
            # Clean expired zones first (memory only, database cleanup in single session)
            await self._remove_expired_zones_memory_only(symbol)

            # Collect zones to save/update in database
            zones_to_save = []
            zones_to_update = []

            # Update existing zones or add new ones
            for new_zone in zones:
                existing_zone = self._find_similar_zone(symbol, new_zone)
                if existing_zone:
                    # Update existing zone: update last_tested and touches
                    existing_zone.last_tested = new_zone.last_tested
                    existing_zone.touches += 1
                    # Update strength if new zone is stronger
                    if new_zone.strength > existing_zone.strength:
                        existing_zone.strength = new_zone.strength
                    logger.debug(f"Updated existing zone for {symbol}")
                    zones_to_update.append(existing_zone)
                else:
                    # Add new zone
                    self.zones[symbol].append(new_zone)
                    zones_to_save.append(new_zone)

            # Determine zones to remove (for limiting)
            removed_zones = []
            if len(self.zones[symbol]) > self.max_zones_per_symbol:
                # Sort by strength (descending) and keep top N
                self.zones[symbol].sort(key=lambda z: z.strength, reverse=True)
                removed_zones = self.zones[symbol][self.max_zones_per_symbol :]
                self.zones[symbol] = self.zones[symbol][: self.max_zones_per_symbol]

            # All database operations in single session
            if self.use_database:
                await self._execute_all_db_operations(
                    symbol, zones_to_save, zones_to_update, removed_zones, timeframe
                )

        logger.debug(
            f"Zones for {symbol}: {len(self.zones[symbol])} total "
            f"(added/updated {len(zones)} new zones)"
        )

    def _find_similar_zone(self, symbol: str, zone: DetectedZone) -> DetectedZone | None:
        """
        Find similar zone (overlapping or very close) for update.

        Args:
            symbol: Trading symbol
            zone: Zone to find similar for

        Returns:
            Similar zone if found, None otherwise
        """
        if symbol not in self.zones:
            return None

        for existing_zone in self.zones[symbol]:
            # Check if zones overlap or are very close (within 5 pips)
            if existing_zone.zone_type != zone.zone_type:
                continue

            # Check overlap
            if self._zones_overlap(existing_zone, zone):
                return existing_zone

            # Check if very close (within 5 pips)
            distance_pips = abs(existing_zone.midpoint - zone.midpoint) * 10000
            if distance_pips < 5:
                return existing_zone

        return None

    def _zones_overlap(self, zone1: DetectedZone, zone2: DetectedZone) -> bool:
        """Check if two zones overlap."""
        return not (zone1.upper_bound < zone2.lower_bound or zone1.lower_bound > zone2.upper_bound)

    async def _remove_expired_zones_memory_only(self, symbol: str) -> None:
        """Remove expired zones from memory only (database cleanup done separately)."""
        if symbol not in self.zones:
            return

        current_time = datetime.now()  # Timezone-naive for comparison
        initial_count = len(self.zones[symbol])

        self.zones[symbol] = [
            zone
            for zone in self.zones[symbol]
            if (
                current_time
                - (
                    zone.first_detected.replace(tzinfo=None)
                    if zone.first_detected.tzinfo is not None
                    else zone.first_detected
                )
            ).total_seconds()
            / 3600
            <= self.max_zone_age_hours
        ]

        removed_count = initial_count - len(self.zones[symbol])
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} expired zones from memory for {symbol}")

    def update_zones_with_current_price(
        self, symbol: str, current_price: float, current_time: datetime
    ) -> None:
        """
        Update zones when price touches them.

        Args:
            symbol: Trading symbol
            current_price: Current market price
            current_time: Current timestamp
        """
        if symbol not in self.zones:
            return

        for zone in self.zones[symbol]:
            # Check if price is touching the zone
            if zone.lower_bound <= current_price <= zone.upper_bound:
                zone.last_tested = current_time
                zone.touches += 1
                logger.debug(f"Zone touched for {symbol} at {current_price}")

    def get_zones(self, symbol: str, zone_type: ZoneType | None = None) -> list[DetectedZone]:
        """Get zones for a symbol, optionally filtered by type."""
        if symbol not in self.zones:
            return []

        zones = self.zones[symbol]

        if zone_type is not None:
            zones = [z for z in zones if z.zone_type == zone_type]

        return zones

    def clear_zones(self, symbol: str) -> None:
        """Clear all zones for a symbol."""
        if symbol in self.zones:
            del self.zones[symbol]
            logger.debug(f"Cleared zones for {symbol}")

    # Database operations

    def _generate_zone_id(self, symbol: str, zone: DetectedZone) -> str:
        """Generate unique zone ID."""
        return f"{symbol}_{zone.zone_type.value}_{zone.lower_bound:.5f}_{zone.upper_bound:.5f}"

    def _detected_zone_to_db_model(
        self, symbol: str, zone: DetectedZone, timeframe: str
    ) -> SupplyDemandZone:
        """Convert DetectedZone to SupplyDemandZone database model."""
        zone_id = self._generate_zone_id(symbol, zone)
        return SupplyDemandZone(
            zone_id=zone_id,
            symbol=symbol,
            zone_type=zone.zone_type.value,
            high_price=zone.upper_bound,
            low_price=zone.lower_bound,
            entry_price=zone.midpoint,
            strength=zone.strength,
            touched_count=zone.touches,
            volume_confirmed=zone.volume_confirmed,
            timeframe=timeframe,
            first_detected=(
                zone.first_detected.replace(tzinfo=None)
                if zone.first_detected.tzinfo is not None
                else zone.first_detected
            ),
            last_touched=(
                (
                    zone.last_tested.replace(tzinfo=None)
                    if zone.last_tested and zone.last_tested.tzinfo is not None
                    else zone.last_tested
                )
                if zone.last_tested
                else None
            ),
            is_active=True,
        )

    def _db_model_to_detected_zone(self, db_zone: SupplyDemandZone) -> DetectedZone:
        """Convert SupplyDemandZone database model to DetectedZone."""
        return DetectedZone(
            zone_type=ZoneType(db_zone.zone_type),
            upper_bound=db_zone.high_price,
            lower_bound=db_zone.low_price,
            strength=db_zone.strength,
            touches=db_zone.touched_count,
            volume_confirmed=db_zone.volume_confirmed,
            first_detected=(
                db_zone.first_detected.replace(tzinfo=None)
                if db_zone.first_detected.tzinfo
                else db_zone.first_detected
            ),
            last_tested=(
                db_zone.last_touched.replace(tzinfo=None)
                if db_zone.last_touched and db_zone.last_touched.tzinfo
                else db_zone.last_touched or db_zone.first_detected.replace(tzinfo=None)
            ),
        )

    async def _execute_all_db_operations(
        self,
        symbol: str,
        zones_to_save: list[DetectedZone],
        zones_to_update: list[DetectedZone],
        removed_zones: list[DetectedZone],
        timeframe: str,
    ) -> None:
        """Execute all database operations in single session."""
        if not self.use_database:
            return

        try:
            # Single session for all operations
            # Context manager handles commit/rollback/close automatically
            async with get_session() as session:
                # 1. Deactivate expired zones - wait for query to complete
                expired_result = await session.execute(
                    select(SupplyDemandZone).where(
                        SupplyDemandZone.symbol == symbol,
                        SupplyDemandZone.is_active,
                    )
                )
                all_db_zones = list(expired_result.scalars().all())  # Materialize immediately
                current_time = datetime.now()  # Timezone-naive for comparison with DB values
                for db_zone in all_db_zones:
                    # Ensure both are timezone-naive for comparison
                    first_detected = db_zone.first_detected
                    if first_detected.tzinfo is not None:
                        first_detected = first_detected.replace(tzinfo=None)
                    age_hours = (current_time - first_detected).total_seconds() / 3600
                    if age_hours > self.max_zone_age_hours:
                        db_zone.is_active = False
                        db_zone.updated_at = current_time

                # 2. Deactivate removed zones (from limiting) - wait for query to complete
                if removed_zones:
                    removed_zone_ids = [
                        self._generate_zone_id(symbol, zone) for zone in removed_zones
                    ]
                    if removed_zone_ids:
                        removed_result = await session.execute(
                            select(SupplyDemandZone).where(
                                SupplyDemandZone.zone_id.in_(removed_zone_ids)
                            )
                        )
                        removed_db_zones = list(
                            removed_result.scalars().all()
                        )  # Materialize immediately
                        for db_zone in removed_db_zones:
                            db_zone.is_active = False
                            db_zone.updated_at = current_time  # Already timezone-naive

                # 3. Save/update new zones - wait for query to complete
                if zones_to_save or zones_to_update:
                    # Collect all zone IDs to check in batch
                    all_zone_ids = [
                        self._generate_zone_id(symbol, zone)
                        for zone in zones_to_save + zones_to_update
                    ]

                    # Batch query all zones at once - wait for query to complete
                    if all_zone_ids:
                        existing_result = await session.execute(
                            select(SupplyDemandZone).where(
                                SupplyDemandZone.zone_id.in_(all_zone_ids)
                            )
                        )
                        existing_zones = {
                            zone.zone_id: zone for zone in existing_result.scalars().all()
                        }  # Materialize immediately
                    else:
                        existing_zones = {}

                    # Process zones to save (new zones)
                    for zone in zones_to_save:
                        zone_id = self._generate_zone_id(symbol, zone)
                        existing = existing_zones.get(zone_id)

                        if existing:
                            # Update existing zone
                            existing.high_price = zone.upper_bound
                            existing.low_price = zone.lower_bound
                            existing.strength = zone.strength
                            existing.touched_count = zone.touches
                            existing.volume_confirmed = zone.volume_confirmed
                            # Ensure timezone-naive datetime for DB
                            if zone.last_tested:
                                existing.last_touched = (
                                    zone.last_tested.replace(tzinfo=None)
                                    if zone.last_tested.tzinfo is not None
                                    else zone.last_tested
                                )
                            existing.is_active = True
                            existing.updated_at = datetime.now()  # Timezone-naive for DB
                            self._zone_id_map[zone_id] = existing.id
                        else:
                            # Create new zone
                            db_zone = self._detected_zone_to_db_model(symbol, zone, timeframe)
                            session.add(db_zone)
                            await session.flush()  # Get the ID - wait for flush to complete
                            self._zone_id_map[zone_id] = db_zone.id

                    # Process zones to update (existing zones in memory)
                    for zone in zones_to_update:
                        zone_id = self._generate_zone_id(symbol, zone)
                        existing = existing_zones.get(zone_id)

                        if existing:
                            # Update existing zone in database
                            existing.high_price = zone.upper_bound
                            existing.low_price = zone.lower_bound
                            existing.strength = zone.strength
                            existing.touched_count = zone.touches
                            existing.volume_confirmed = zone.volume_confirmed
                            # Ensure timezone-naive datetime for DB
                            if zone.last_tested:
                                existing.last_touched = (
                                    zone.last_tested.replace(tzinfo=None)
                                    if zone.last_tested.tzinfo is not None
                                    else zone.last_tested
                                )
                            existing.is_active = True
                            existing.updated_at = datetime.now()  # Timezone-naive for DB

                # Manual commit after all operations complete
                await session.commit()
                logger.debug(
                    f"Executed all DB operations for {symbol}: "
                    f"saved {len(zones_to_save)} new, updated {len(zones_to_update)}, "
                    f"deactivated {len(removed_zones)} removed zones"
                )

        except Exception as e:
            logger.error(f"Error executing database operations: {e}", exc_info=True)

    async def _batch_save_zones_to_db(
        self,
        symbol: str,
        zones_to_save: list[DetectedZone],
        zones_to_update: list[DetectedZone],
        timeframe: str,
    ) -> None:
        """Batch save/update zones (legacy method, use _execute_all_db_operations instead)."""
        await self._execute_all_db_operations(symbol, zones_to_save, zones_to_update, [], timeframe)

    async def _save_zone_to_db(self, symbol: str, zone: DetectedZone, timeframe: str) -> None:
        """Save zone to database (legacy method)."""
        await self._execute_all_db_operations(symbol, [zone], [], [], timeframe)

    async def _update_zone_in_db(self, symbol: str, zone: DetectedZone, timeframe: str) -> None:
        """Update zone in database (legacy method)."""
        await self._execute_all_db_operations(symbol, [], [zone], [], timeframe)

    async def _deactivate_expired_zones(self, symbol: str) -> None:
        """Deactivate expired zones in database."""
        if not self.use_database:
            return

        try:
            # Note: Lock should be acquired by caller (add_zones)
            async with get_session() as session:
                result = await session.execute(
                    select(SupplyDemandZone).where(
                        SupplyDemandZone.symbol == symbol,
                        SupplyDemandZone.is_active,
                    )
                )
                zones = result.scalars().all()

                current_time = datetime.now()  # Timezone-naive for comparison with DB values
                for db_zone in zones:
                    # Ensure both are timezone-naive for comparison
                    first_detected = db_zone.first_detected
                    if first_detected.tzinfo is not None:
                        first_detected = first_detected.replace(tzinfo=None)
                    age_hours = (current_time - first_detected).total_seconds() / 3600
                    if age_hours > self.max_zone_age_hours:
                        db_zone.is_active = False
                        db_zone.updated_at = current_time

                await session.commit()
                logger.debug(f"Deactivated expired zones for {symbol}")

        except Exception as e:
            logger.error(f"Error deactivating expired zones: {e}", exc_info=True)

    async def _deactivate_zones(self, symbol: str, zones: list[DetectedZone]) -> None:
        """Deactivate specific zones in database."""
        if not self.use_database:
            return

        try:
            # Note: Lock should be acquired by caller (add_zones)
            async with get_session() as session:
                # Collect all zone IDs for batch query
                zone_ids = [self._generate_zone_id(symbol, zone) for zone in zones]
                if zone_ids:
                    result = await session.execute(
                        select(SupplyDemandZone).where(SupplyDemandZone.zone_id.in_(zone_ids))
                    )
                    db_zones = result.scalars().all()
                    current_time = datetime.now()  # Timezone-naive for DB
                    for db_zone in db_zones:
                        db_zone.is_active = False
                        db_zone.updated_at = current_time

                await session.commit()
                logger.debug(f"Deactivated {len(zones)} zones for {symbol}")

        except Exception as e:
            logger.error(f"Error deactivating zones: {e}", exc_info=True)

    async def load_zones_from_db(self, symbol: str) -> None:
        """Load active zones from database for a symbol."""
        if not self.use_database:
            return

        try:
            async with self._db_lock:
                async with get_session() as session:
                    result = await session.execute(
                        select(SupplyDemandZone).where(
                            SupplyDemandZone.symbol == symbol,
                            SupplyDemandZone.is_active,
                        )
                    )
                    db_zones = result.scalars().all()

                    if not db_zones:
                        logger.debug(f"No zones found in database for {symbol}")
                        return

                    # Convert to DetectedZone and add to memory
                    if symbol not in self.zones:
                        self.zones[symbol] = []

                    for db_zone in db_zones:
                        detected_zone = self._db_model_to_detected_zone(db_zone)
                        self.zones[symbol].append(detected_zone)
                        self._zone_id_map[db_zone.zone_id] = db_zone.id

                    logger.info(f"Loaded {len(db_zones)} zones from database for {symbol}")

        except Exception as e:
            logger.error(f"Error loading zones from database: {e}", exc_info=True)
