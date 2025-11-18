import os
import time
import logging
from datetime import datetime
from typing import Optional
import numpy as np

from interfaces.base import ICamera, IDetector, INotifier
from config.settings import MonitorConfig, GeneratorState
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

        self._current_state: GeneratorState = GeneratorState.UNKNOWN
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
        self._logger.info("🚀 Запуск системи моніторингу")
        self._logger.info("=" * 40)

        self._send_startup_notification()
        self._main_loop()

    def stop(self):
        """Зупинка моніторингу"""
        self._is_running = False
        self._camera.disconnect()
        self._send_shutdown_notification()

        self._logger.info("🛑 Моніторинг зупинено")

    def _main_loop(self):
        """Основний цикл моніторингу"""
        while self._is_running:
            try:
                # Підключення до камери
                if not self._camera.is_connected():
                    if not self._camera.connect():
                        self._logger.warning(
                            f"Повторна спроба через {self._config.reconnect_delay} сек..."
                        )
                        time.sleep(self._config.reconnect_delay)
                        continue

                # Отримання та обробка кадру
                ret, frame = self._camera.get_frame()

                if not ret or frame is None:
                    self._logger.warning(
                        "Не вдалося отримати кадр. Переподключення..."
                    )
                    self._camera.disconnect()
                    time.sleep(self._config.reconnect_delay)
                    continue

                # Визначення стану
                self._process_frame(frame)

                # Затримка
                time.sleep(self._config.check_interval)

            except KeyboardInterrupt:
                self._logger.info("⚠️ Отримано сигнал зупинки")
                break
            except Exception as e:
                self._logger.error(f"Помилка в циклі: {e}")
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
        """Обробка зміни стану"""
        is_on = self._current_state == GeneratorState.ON
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Логування
        emoji = "🟢" if is_on else "🔴"
        status = "УВІМКНЕНО" if is_on else "ВИМКНЕНО"
        self._logger.info(f"{emoji} Генератор {status}")

        # Створення повідомлення
        message = self._create_state_message(is_on, timestamp, bright_pixels)

        # Візуалізація
        visual_frame = self._visualizer.visualize(
            frame, self._detector.roi, is_on, bright_pixels
        )

        # Відправка сповіщень
        self._notifier.send_message(message)

        caption = f"{emoji} <b>{status}</b>\n{timestamp}"
        self._notifier.send_image(visual_frame, caption)

        # Збереження знімка
        self._save_snapshot(
            visual_frame, "generator_on" if is_on else "generator_off"
        )

    @staticmethod
    def _create_state_message(
            is_on: bool, timestamp: str, bright_pixels: int
    ) -> str:
        """Створення повідомлення про стан"""
        emoji = "🟢" if is_on else "🔴"
        status = "УВІМКНЕНО" if is_on else "ВИМКНЕНО"
        lamp_status = "світиться" if is_on else "не світиться"

        message = f"{emoji} <b>ГЕНЕРАТОР {status}</b>\n\n"
        message += f"⏰ Час: {timestamp}\n"
        message += f"💡 Лампочка {lamp_status}\n"
        message += f"📊 Яскравих пікселів: {bright_pixels}"

        return message

    def _save_snapshot(self, frame: np.ndarray, prefix: str):
        """Збереження знімка"""
        import cv2

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(
            self._config.snapshot_folder, f"{prefix}_{timestamp}.jpg"
        )
        cv2.imwrite(filename, frame)
        self._logger.info(f"💾 Знімок: {filename}")

    def _send_startup_notification(self):
        """Сповіщення про запуск"""
        message = f"""
🚀 <b>МОНІТОРИНГ ЗАПУЩЕНО</b>

⏰ Час: {self._start_time.strftime("%d.%m.%Y %H:%M:%S")}
📹 Камера: {self._config.camera.ip}
🔄 Інтервал: {self._config.check_interval} сек.

Система активна.
"""
        self._notifier.send_message(message)

    def _send_shutdown_notification(self):
        """Сповіщення про зупинку"""
        if self._start_time:
            duration = datetime.now() - self._start_time
            hours = duration.total_seconds() / 3600

            message = f"""
🛑 <b>МОНІТОРИНГ ЗУПИНЕНО</b>

⏰ Час: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}
⏱️ Тривалість: {hours:.2f} год.
🔄 Змін стану: {self._state_change_count}

Система зупинена.
"""
            self._notifier.send_message(message)
