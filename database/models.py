"""
Моделі даних для SQLite бази даних
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GeneratorSession:
    """
    Модель сесії роботи генератора
    (від увімкнення до вимкнення)
    """

    id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    duration_hours: Optional[float] = None
    fuel_consumption_liters: Optional[float] = None
    start_bright_pixels: Optional[int] = None
    end_bright_pixels: Optional[int] = None
    notes: Optional[str] = None

    def calculate_duration(self):
        """Розрахунок тривалості"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = int(delta.total_seconds())
            self.duration_hours = delta.total_seconds() / 3600

    def calculate_fuel_consumption(self, fuel_rate_per_hour: float = 1.5):
        """
        Розрахунок витрат палива

        Args:
            fuel_rate_per_hour: Витрати палива л/год (за замовчуванням 1.5 л/год)
        """
        if self.duration_hours:
            self.fuel_consumption_liters = (
                self.duration_hours * fuel_rate_per_hour
            )


@dataclass
class GeneratorEvent:
    """
    Модель події генератора
    (кожна зміна стану)
    """

    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    event_type: Optional[str] = None  # 'ON', 'OFF', 'ERROR'
    bright_pixels: Optional[int] = None
    message: Optional[str] = None


@dataclass
class FuelConfig:
    """
    Конфігурація витрат палива
    """

    fuel_rate_per_hour: float = 1.4  # л/год
    fuel_tank_capacity: float = 6.0  # л
    fuel_price_per_liter: float = 60.0  # грн/л
