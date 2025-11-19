from config.settings import (
    MonitorConfig,
    CameraConfig,
    DetectionConfig,
    TelegramConfig,
)
from hardware.camera import IPCamera
from detection.detector import BrightSpotDetector
from notification.telegram import TelegramNotifier
from core.monitor import GeneratorMonitor
from utils.logger import setup_logging

from environs import Env

# Читання змінних середовища
env = Env()
env.read_env()


def main():
    """Головна функція"""

    # Налаштування логування
    setup_logging()

    # Конфігурація системи
    config = MonitorConfig(
        camera=CameraConfig(
            username=env.str("CAMERA_USERNAME"),
            password=env.str("CAMERA_PASSWORD"),
            ip=env.str("CAMERA_IP"),
            port=env.int("CAMERA_PORT"),
            stream_path=env.str("CAMERA_RTSP_URL"),
        ),
        detection=DetectionConfig(
            roi=(485, 435, 40, 20),
            bright_threshold=190,
            min_bright_pixels=50,
        ),
        telegram=TelegramConfig(
            bot_token=env.str("TELEGRAM_BOT_TOKEN"),
            chat_id=env.str("TELEGRAM_CHAT_ID"),
        ),
        check_interval=5,
        reconnect_delay=30,
    )

    # Створення компонентів
    camera = IPCamera(config.camera)
    detector = BrightSpotDetector(config.detection)
    notifier = TelegramNotifier(config.telegram)

    # Створення та запуск моніторингу
    monitor = GeneratorMonitor(config, camera, detector, notifier)

    try:
        monitor.start()
    except KeyboardInterrupt:
        print("⚠️ Зупинка системи...")
        monitor.stop()
    except Exception as e:
        import logging

        logging.error(f"Критична помилка: {e}")
        monitor.stop()


if __name__ == "__main__":
    main()
