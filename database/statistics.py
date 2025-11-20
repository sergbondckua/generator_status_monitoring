"""
Статистика та звіти
"""

import logging
from datetime import datetime, timedelta
from typing import List
from dataclasses import dataclass

from database.repository import DatabaseRepository


@dataclass
class DailyStats:
    """Статистика за день"""

    date: str
    total_runtime_hours: float | None
    total_fuel_liters: float | None
    total_cost: float
    sessions_count: int
    avg_session_duration: float


@dataclass
class MonthlyStats:
    """Статистика за місяць"""

    month: str
    total_runtime_hours: float | None
    total_fuel_liters: float | None
    total_cost: float
    sessions_count: int
    daily_stats: List[DailyStats]


class StatisticsService:
    """Сервіс для роботи зі статистикою"""

    def __init__(self, repository: DatabaseRepository):
        """
        Ініціалізація сервісу

        Args:
            repository: Репозиторій БД
        """
        self._repo = repository
        self._logger = logging.getLogger(self.__class__.__name__)

    def get_today_stats(self) -> DailyStats:
        """Статистика за сьогодні"""
        today = datetime.now().date()
        return self._get_stats_for_date(today)

    def get_yesterday_stats(self) -> DailyStats:
        """Статистика за вчора"""
        yesterday = datetime.now().date() - timedelta(days=1)
        return self._get_stats_for_date(yesterday)

    def get_week_stats(self) -> List[DailyStats]:
        """Статистика за тиждень"""
        stats = []
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            stats.append(self._get_stats_for_date(date))
        return stats

    def get_month_stats(
        self, year: int = None, month: int = None
    ) -> MonthlyStats:
        """
        Статистика за місяць

        Args:
            year: Рік (за замовчуванням поточний)
            month: Місяць (за замовчуванням поточний)

        Returns:
            Статистика за місяць
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        # Отримуємо всі сесії за місяць
        sessions = self._repo.get_all_sessions(limit=1000)

        month_sessions = [
            s
            for s in sessions
            if s.start_time
            and s.start_time.year == year
            and s.start_time.month == month
        ]

        # Розраховуємо загальну статистику
        total_runtime = sum(s.duration_hours or 0 for s in month_sessions)
        total_fuel = sum(
            s.fuel_consumption_liters or 0 for s in month_sessions
        )

        fuel_config = self._repo.get_fuel_config()
        total_cost = total_fuel * fuel_config.fuel_price_per_liter

        # Статистика по днях
        daily_stats = {}
        for session in month_sessions:
            date_str = session.start_time.strftime("%Y-%m-%d")
            if date_str not in daily_stats:
                daily_stats[date_str] = {"runtime": 0, "fuel": 0, "count": 0}
            daily_stats[date_str]["runtime"] += session.duration_hours or 0
            daily_stats[date_str]["fuel"] += (
                session.fuel_consumption_liters or 0
            )
            daily_stats[date_str]["count"] += 1

        daily_stats_list = []
        for date_str, stats in daily_stats.items():
            daily_stats_list.append(
                DailyStats(
                    date=date_str,
                    total_runtime_hours=stats["runtime"],
                    total_fuel_liters=stats["fuel"],
                    total_cost=stats["fuel"]
                    * fuel_config.fuel_price_per_liter,
                    sessions_count=stats["count"],
                    avg_session_duration=(
                        stats["runtime"] / stats["count"]
                        if stats["count"] > 0
                        else 0
                    ),
                )
            )

        return MonthlyStats(
            month=f"{year}-{month:02d}",
            total_runtime_hours=total_runtime,
            total_fuel_liters=total_fuel,
            total_cost=total_cost,
            sessions_count=len(month_sessions),
            daily_stats=sorted(daily_stats_list, key=lambda x: x.date),
        )

    def _get_stats_for_date(self, date) -> DailyStats:
        """Статистика за конкретну дату"""
        sessions = self._repo.get_all_sessions(limit=1000)

        day_sessions = [
            s for s in sessions if s.start_time and s.start_time.date() == date
        ]

        total_runtime = sum(s.duration_hours or 0 for s in day_sessions)
        total_fuel = sum(s.fuel_consumption_liters or 0 for s in day_sessions)

        fuel_config = self._repo.get_fuel_config()
        total_cost = total_fuel * fuel_config.fuel_price_per_liter

        avg_duration = total_runtime / len(day_sessions) if day_sessions else 0

        return DailyStats(
            date=date.strftime("%Y-%m-%d"),
            total_runtime_hours=total_runtime,
            total_fuel_liters=total_fuel,
            total_cost=total_cost,
            sessions_count=len(day_sessions),
            avg_session_duration=avg_duration,
        )

    def get_formatted_report(self, period: str = "today") -> str:
        """
        Отримання форматованого звіту

        Args:
            period: Період ('today', 'yesterday', 'week', 'month')

        Returns:
            Текстовий звіт
        """
        if period == "today":
            stats = self.get_today_stats()
            return self._format_daily_report(stats, "Сьогодні")

        elif period == "yesterday":
            stats = self.get_yesterday_stats()
            return self._format_daily_report(stats, "Вчора")

        elif period == "week":
            week_stats = self.get_week_stats()
            return self._format_week_report(week_stats)

        elif period == "month":
            month_stats = self.get_month_stats()
            return self._format_month_report(month_stats)

        return "Невідомий період"

    def _format_daily_report(self, stats: DailyStats, title: str) -> str:
        """Форматування денного звіту"""
        report = f"""
📊 <b>Звіт: {title}</b>
📅 Дата: {stats.date}

⏱️ Час роботи: {stats.total_runtime_hours:.2f} год
⛽ Витрати палива: {stats.total_fuel_liters:.2f} л
💰 Вартість: {stats.total_cost:.2f} грн
🔄 Кількість запусків: {stats.sessions_count}
📈 Середня тривалість: {stats.avg_session_duration:.2f} год
"""
        return report.strip()

    def _format_week_report(self, week_stats: List[DailyStats]) -> str:
        """Форматування тижневого звіту"""
        total_runtime = sum(s.total_runtime_hours for s in week_stats)
        total_fuel = sum(s.total_fuel_liters for s in week_stats)
        total_cost = sum(s.total_cost for s in week_stats)
        total_sessions = sum(s.sessions_count for s in week_stats)

        report = f"""
📊 <b>Тижневий звіт</b>
📅 Останні 7 днів

⏱️ Загальний час: {total_runtime:.2f} год
⛽ Загальні витрати: {total_fuel:.2f} л
💰 Загальна вартість: {total_cost:.2f} грн
🔄 Всього запусків: {total_sessions}

По днях:
"""
        for stats in reversed(week_stats):
            report += f"\n{stats.date}: {stats.total_runtime_hours:.1f}год, {stats.total_fuel_liters:.1f}л"

        return report.strip()

    def _format_month_report(self, stats: MonthlyStats) -> str:
        """Форматування місячного звіту"""
        report = f"""
📊 <b>Місячний звіт</b>
📅 Місяць: {stats.month}

⏱️ Загальний час: {stats.total_runtime_hours:.2f} год
⛽ Загальні витрати: {stats.total_fuel_liters:.2f} л
💰 Загальна вартість: {stats.total_cost:.2f} грн
🔄 Всього запусків: {stats.sessions_count}
📈 Середньо на день: {stats.total_runtime_hours / max(len(stats.daily_stats), 1):.2f} год
"""
        return report.strip()
