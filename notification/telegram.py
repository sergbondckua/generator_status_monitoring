import cv2
import requests
import logging
import numpy as np

from interfaces.base import INotifier
from config.settings import TelegramConfig


class TelegramNotifier(INotifier):
    """Telegram нотифікатор"""

    def __init__(self, config: TelegramConfig):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        config.validate()

        self._base_url = f"https://api.telegram.org/bot{config.bot_token}"

    def send_message(self, message: str) -> bool:
        """Відправка текстового повідомлення"""
        url = f"{self._base_url}/sendMessage"
        data = {
            "chat_id": self._config.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                self._logger.info("✅ Повідомлення надіслано")
                return True
            else:
                self._logger.error(f"Помилка: {response.status_code}")
                return False

        except Exception as e:
            self._logger.error(f"Помилка відправки: {e}")
            return False

    def send_image(self, image: np.ndarray, caption: str) -> bool:
        """Відправка зображення"""
        url = f"{self._base_url}/sendPhoto"

        try:
            # Конвертуємо в JPEG
            _, img_encoded = cv2.imencode(".jpg", image)

            files = {
                "photo": ("image.jpg", img_encoded.tobytes(), "image/jpeg")
            }
            data = {
                "chat_id": self._config.chat_id,
                "caption": caption,
                "parse_mode": "HTML",
            }

            response = requests.post(url, files=files, data=data, timeout=30)

            if response.status_code == 200:
                self._logger.info("✅ Фото надіслано")
                return True
            else:
                self._logger.error(f"Помилка фото: {response.status_code}")
                return False

        except Exception as e:
            self._logger.error(f"Помилка відправки фото: {e}")
            return False
