"""
Репозиторій для роботи з базою даних.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Optional

import pytz

# Ваші моделі (замініть на ваші імпорти)
from database.models import GeneratorSession, GeneratorEvent, FuelConfig


class DatabaseRepository:
    """
    Репозиторій для роботи з SQLite базою даних.
    """

    def __init__(self, db_path: str = "generator_monitor.db"):
        self._db_path = db_path
        # Ініціалізація часового поясу через pytz
        self._tz = pytz.timezone("Europe/Kyiv")
        self._logger = logging.getLogger(self.__class__.__name__)
        self._init_database()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            self._logger.error(f"Помилка БД: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Ініціалізація структури БД."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблиці залишаються без змін
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generator_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER,
                    duration_hours REAL,
                    fuel_consumption_liters REAL,
                    start_bright_pixels INTEGER,
                    end_bright_pixels INTEGER,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generator_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    event_type TEXT NOT NULL,
                    bright_pixels INTEGER,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fuel_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    fuel_rate_per_hour REAL NOT NULL,
                    fuel_tank_capacity REAL NOT NULL,
                    fuel_price_per_liter REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            cursor.execute("SELECT COUNT(*) FROM fuel_config WHERE id = 1")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO fuel_config (id, fuel_rate_per_hour, fuel_tank_capacity, fuel_price_per_liter)
                    VALUES (1, 1.5, 20.0, 50.0)
                """
                )

    # ========== HELPER METHODS ==========

    def _get_current_time(self) -> datetime:
        """Повертає поточний час у зоні Europe/Kyiv."""
        # У pytz метод now(tz) працює коректно
        return datetime.now(self._tz)

    def _parse_db_datetime(self, db_val: str) -> Optional[datetime]:
        """
        Безпечно парсить час з БД.
        Адаптовано для pytz (використовує localize замість replace).
        """
        if not db_val:
            return None

        # fromisoformat доступний у Python 3.7+
        dt = datetime.fromisoformat(db_val)

        # Якщо дата "нативна" (без часового поясу), додаємо його
        if dt.tzinfo is None:
            # Треба використовувати .localize()
            dt = self._tz.localize(dt)

        return dt

    def _map_row_to_session(self, row: sqlite3.Row) -> GeneratorSession:
        return GeneratorSession(
            id=row["id"],
            start_time=self._parse_db_datetime(row["start_time"]),
            end_time=self._parse_db_datetime(row["end_time"]),
            duration_seconds=row["duration_seconds"],
            duration_hours=row["duration_hours"],
            fuel_consumption_liters=row["fuel_consumption_liters"],
            start_bright_pixels=row["start_bright_pixels"],
            end_bright_pixels=row["end_bright_pixels"],
            notes=row["notes"],
        )

    def _map_row_to_event(self, row: sqlite3.Row) -> GeneratorEvent:
        return GeneratorEvent(
            id=row["id"],
            timestamp=self._parse_db_datetime(row["timestamp"]),
            event_type=row["event_type"],
            bright_pixels=row["bright_pixels"],
            message=row["message"],
        )

    # ========== РОБОТА З СЕСІЯМИ ==========

    def start_session(self, bright_pixels: int) -> int:
        """
        Розпочати сесію генераторатора.

        Args:
            bright_pixels: Число яскравих пікселів на момент запуску сесії.

        Returns:
            int: Ідентифікатор нової сесії.
        """
        start_time = self._get_current_time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO generator_sessions (start_time, start_bright_pixels) VALUES (?, ?)",
                (start_time, bright_pixels),
            )
            session_id = cursor.lastrowid

            time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            self._logger.info(
                f"🟢 [Kyiv: {time_str}] Розпочато сесію #{session_id}"
            )
            return session_id

    def end_session(
        self, session_id: int, bright_pixels: int, notes: Optional[str] = None
    ) -> None:
        """
        Завершити сесію генераторатора.

        Args:
            session_id: int: Ідентифікатор сесії, яку потрібно завершити.
            bright_pixels: int: Число яскравих пікселів на момент завершення сесії.
            notes: Optional[str]: Зауважка до сесії (необов'язково).

        Returns:
            None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT start_time FROM generator_sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()

            if not row:
                self._logger.error(f"❌ Сесія #{session_id} не знайдена.")
                return

            start_time = self._parse_db_datetime(row["start_time"])
            end_time = self._get_current_time()

            # Розрахунок різниці
            duration = end_time - start_time
            duration_seconds = int(duration.total_seconds())
            duration_hours = duration.total_seconds() / 3600.0

            fuel_config = self.get_fuel_config()
            fuel_consumption = duration_hours * fuel_config.fuel_rate_per_hour

            cursor.execute(
                """
                UPDATE generator_sessions
                SET end_time = ?,
                    duration_seconds = ?,
                    duration_hours = ?,
                    fuel_consumption_liters = ?,
                    end_bright_pixels = ?,
                    notes = ?
                WHERE id = ?
            """,
                (
                    end_time,
                    duration_seconds,
                    duration_hours,
                    fuel_consumption,
                    bright_pixels,
                    notes,
                    session_id,
                ),
            )

            self._logger.info(
                f"🔴 Завершено сесію #{session_id}. "
                f"Тривалість: {duration_hours:.2f} год. Спожито: {fuel_consumption:.2f} л"
            )

    def get_active_session(self) -> Optional[int]:
        """
        Отримати активну сесію генераторатора.

        Returns:
            Optional[int]: Ідентифікатор активної сесії, якщо така знайдена, або None, якщо активна сесія не знайдена.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM generator_sessions
                WHERE end_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
            """
            )
            row = cursor.fetchone()
            return row["id"] if row else None

    def get_session(self, session_id: int) -> Optional[GeneratorSession]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM generator_sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            return self._map_row_to_session(row) if row else None

    def get_all_sessions(self, limit: int = 100) -> List[GeneratorSession]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM generator_sessions ORDER BY start_time DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [self._map_row_to_session(row) for row in rows]

    # ========== РОБОТА З ПОДІЯМИ ==========

    def add_event(
        self,
        event_type: str,
        bright_pixels: int,
        message: Optional[str] = None,
    ) -> int:
        """
        Додати подію до БД події генераторатора.

        Args:
            event_type: str: Тип події (наприклад, "lamp_on" або "lamp_off").
            bright_pixels: int: Число яскравих пікселів на момент події.
            message: Optional[str]: Зауважка до події (необов'язково).

        Returns:
            int: Ідентифікатор нової події.
        """
        timestamp = self._get_current_time()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO generator_events (timestamp, event_type, bright_pixels, snapshot_path, message)
                VALUES (?, ?, ?, ?)
            """,
                (timestamp, event_type, bright_pixels, message),
            )
            return cursor.lastrowid

    def get_events(
        self, limit: int = 100, event_type: Optional[str] = None
    ) -> List[GeneratorEvent]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM generator_events"
            params = []

            if event_type:
                query += " WHERE event_type = ?"
                params.append(event_type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            return [self._map_row_to_event(row) for row in cursor.fetchall()]

    # ========== КОНФІГУРАЦІЯ ==========

    def get_fuel_config(self) -> FuelConfig:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fuel_config WHERE id = 1")
            row = cursor.fetchone()

            if not row:
                return FuelConfig(1.5, 20.0, 50.0)

            return FuelConfig(
                fuel_rate_per_hour=row["fuel_rate_per_hour"],
                fuel_tank_capacity=row["fuel_tank_capacity"],
                fuel_price_per_liter=row["fuel_price_per_liter"],
            )

    def update_fuel_config(self, config: FuelConfig) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE fuel_config
                SET fuel_rate_per_hour = ?,
                    fuel_tank_capacity = ?,
                    fuel_price_per_liter = ?,
                    updated_at = ?
                WHERE id = 1
            """,
                (
                    config.fuel_rate_per_hour,
                    config.fuel_tank_capacity,
                    config.fuel_price_per_liter,
                    self._get_current_time(),
                ),
            )
            self._logger.info("⚙️ Конфігурацію палива оновлено")
