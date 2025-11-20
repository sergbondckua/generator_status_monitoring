import os
import time
import logging
from datetime import datetime
from typing import Optional
import numpy as np

from database.repository import DatabaseRepository
from database.statistics import StatisticsService
from interfaces.base import ICamera, IDetector, INotifier
from config.settings import MonitorConfig, GeneratorState
import notification.const_text as ct
from visualization.visualizer import FrameVisualizer


class GeneratorMonitor:
    """
    Головний клас моніторингу генератора
    Координує роботу всіх компонентів
    """

    def __init__(
        self,
        config: MonitorConfig,
        camera: ICamera,
        detector: IDetector,
        notifier: INotifier,
        db_repository: DatabaseRepository,
    ):
        """
        Ініціалізація моніторингу

        Args:
            config: Конфігурація
            camera: Реалізація камери
            detector: Реалізація детектора
            notifier: Реалізація нотифікатора
        """
        self._config = config
        self._camera = camera
        self._detector = detector
        self._notifier = notifier
        self._visualizer = FrameVisualizer()
        self._db = db_repository
        self._stats = StatisticsService(db_repository)

        self._current_state: GeneratorState = GeneratorState.UNKNOWN
        self._active_session_id: Optional[int] = None
        self._is_running = False
        self._start_time: Optional[datetime] = None
        self._state_change_count = 0

        self._logger = logging.getLogger(self.__class__.__name__)
        self._setup_folders()

    def _setup_folders(self):
        """Створення необхідних папок"""
        os.makedirs(self._config.snapshot_folder, exist_ok=True)
        os.makedirs(self._config.log_folder, exist_ok=True)

    def start(self):
        """Запуск моніторингу"""
        self._is_running = True
        self._start_time = datetime.now()

        self._logger.info("=" * 40)
        self._logger.info("🚀 Запуск системи моніторингу з БД")
        self._logger.info("=" * 40)

        # Перевіряємо чи є незавершена сесія
        active_session = self._db.get_active_session()
        if active_session:
            self._logger.warning(
                f"Знайдено незавершену сесію #{active_session}"
            )
            self._active_session_id = active_session

        self._send_startup_notification()
        self._main_loop()

    def stop(self):
        """Зупинка"""
        self._is_running = False

        # Завершуємо активну сесію якщо є
        if self._active_session_id:
            self._logger.warning(
                f"Завершення активної сесії #{self._active_session_id}"
            )
            self._db.end_session(
                self._active_session_id, 0, "Система зупинена"
            )

        self._camera.disconnect()
        self._send_shutdown_notification()
        self._logger.info("🛑 Моніторинг зупинено")

    def _main_loop(self):
        """Основний цикл"""
        while self._is_running:
            try:
                if not self._camera.is_connected():
                    if not self._camera.connect():
                        self._logger.warning(
                            f"Повторна спроба через {self._config.reconnect_delay} сек..."
                        )
                        time.sleep(self._config.reconnect_delay)
                        continue

                ret, frame = self._camera.get_frame()

                if not ret or frame is None:
                    self._logger.warning("Не вдалося отримати кадр")
                    self._camera.disconnect()
                    time.sleep(self._config.reconnect_delay)
                    continue

                self._process_frame(frame)
                time.sleep(self._config.check_interval)

            except KeyboardInterrupt:
                self._logger.info("⚠️ Отримано сигнал зупинки")
                self.stop()
                break
            except Exception as e:
                self._logger.error(f"Помилка: {e}")
                time.sleep(10)

    def _process_frame(self, frame: np.ndarray):
        """Обробка кадру"""
        is_detected, bright_pixels = self._detector.detect(frame)
        new_state = GeneratorState.ON if is_detected else GeneratorState.OFF

        # Перевірка зміни стану
        if self._current_state == GeneratorState.UNKNOWN:
            self._current_state = new_state
            self._handle_state_change(frame, bright_pixels)
        elif self._current_state != new_state:
            self._current_state = new_state
            self._state_change_count += 1
            self._handle_state_change(frame, bright_pixels)

    def _handle_state_change(self, frame: np.ndarray, bright_pixels: int):
        """Обробка зміни стану з БД"""
        is_on = self._current_state == GeneratorState.ON
        timestamp = datetime.now()

        # Логування
        emoji = "🟢" if is_on else "🔴"
        status = "УВІМКНЕНО" if is_on else "ВИМКНЕНО"
        self._logger.info(f"{emoji} Генератор {status}")

        # Збереження знімка
        visual_frame = self._visualizer.visualize(
            frame, self._detector.roi, is_on, bright_pixels
        )
        snapshot_path = self._save_snapshot(
            visual_frame, "generator_on" if is_on else "generator_off"
        )

        # Робота з БД
        if is_on:
            # Генератор увімкнено - починаємо нову сесію
            self._active_session_id = self._db.start_session(bright_pixels)
            self._db.add_event("ON", bright_pixels, "Генератор увімкнено")
        else:
            # Генератор вимкнено - завершуємо сесію
            if self._active_session_id:
                self._db.end_session(self._active_session_id, bright_pixels)
                self._active_session_id = None
            self._db.add_event("OFF", bright_pixels, "Генератор вимкнено")

        # Створення повідомлення зі статистикою
        message = self._create_state_message_with_stats(
            is_on, timestamp, bright_pixels
        )

        # Відправка сповіщень
        self._notifier.send_message(message)
        caption = f"{emoji} <b>{status}</b>\n{timestamp.strftime('%d.%m.%Y %H:%M:%S')}"
        self._notifier.send_image(visual_frame, caption)

    def _create_state_message_with_stats(
        self, is_on: bool, timestamp: datetime, bright_pixels: int
    ) -> str:
        """Створення повідомлення зі статистикою"""
        emoji = "🟢" if is_on else "🔴"
        status = "УВІМКНЕНО" if is_on else "ВИМКНЕНО"
        lamp_status = "світиться" if is_on else "не світиться"

        # Створення повідомлення
        message = ct.msg_state_lamp.format(
            emoji=emoji,
            status=status,
            timestamp=timestamp.strftime("%d.%m.%Y %H:%M:%S"),
            lamp_status=lamp_status,
            bright_pixels=bright_pixels,
        )

        # Якщо вимкнено - показуємо статистику останньої сесії
        if not is_on and self._active_session_id:
            session = self._db.get_session(self._active_session_id)
            if session and session.duration_hours:
                fuel_config = self._db.get_fuel_config()
                message += ct.msg_stat_last_session.format(
                    duration_hours=round(session.duration_hours, 2),
                    fuel_consumption_liters=round(
                        session.fuel_consumption_liters, 2
                    ),
                    fuel_cost=round(
                        session.fuel_consumption_liters
                        * fuel_config.fuel_price_per_liter,
                        2,
                    ),
                )

        # Статистика за сьогодні
        today_stats = self._stats.get_today_stats()
        if today_stats.sessions_count > 0:
            message += ct.msg_stat_today.format(
                total_runtime_hours=round(today_stats.total_runtime_hours, 2),
                total_fuel_liters=round(today_stats.total_fuel_liters, 2),
                total_cost=round(today_stats.total_cost, 2),
            )

        return message

    def _save_snapshot(self, frame: np.ndarray, prefix: str) -> str:
        """Збереження знімка"""
        import cv2

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(
            self._config.snapshot_folder, f"{prefix}_{timestamp}.jpg"
        )
        cv2.imwrite(filename, frame)
        self._logger.info(f"💾 Знімок: {filename}")
        return filename

    def _send_startup_notification(self):
        """Сповіщення про запуск моніторингу.
        - час запуску
        - IP-адрес камери
        - інтервал перевір
        """
        # Створення повідомлення
        message = ct.msg_startup_monitor.format(
            start_time=self._start_time.strftime("%d.%m.%Y %H:%M:%S"),
            camera_ip=self._config.camera.ip,
            check_interval=self._config.check_interval,
        )
        # Відправка повідомлення
        self._notifier.send_message(message)

    def _send_shutdown_notification(self):
        """Сповіщення про зупинку"""
        if self._start_time:
            # Оцінка часу роботи
            duration = datetime.now() - self._start_time
            hours = duration.total_seconds() / 3600

            # Створення повідомлення
            message = ct.msg_shutdown_monitor.format(
                date_time=datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                duration=round(hours, 2),
                state_change_count=self._state_change_count,
            )

            # Відправка повідомлення
            self._notifier.send_message(message)

    def send_statistics_report(self, period: str = "today"):
        """
        Відправка звіту зі статистикою

        Args:
            period: Період ('today', 'yesterday', 'week', 'month')
        """
        report = self._stats.get_formatted_report(period)
        self._notifier.send_message(report)
