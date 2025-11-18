import cv2
import logging
from typing import Tuple, Optional
import numpy as np

from interfaces.base import ICamera
from config.settings import CameraConfig


class IPCamera(ICamera):
    """Реалізація IP-камери через RTSP"""

    def __init__(self, config: CameraConfig):
        self._config = config
        self._capture: Optional[cv2.VideoCapture] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        """Підключення до камери"""
        try:
            self._logger.info(f"Підключення до камери {self._config.ip}...")
            self._capture = cv2.VideoCapture(self._config.url)

            if not self._capture.isOpened():
                self._logger.error("Не вдалося відкрити камеру")
                return False

            # Перевірка отримання кадру
            ret, frame = self._capture.read()
            if not ret:
                self._logger.error("Не вдалося отримати кадр")
                self.disconnect()
                return False

            self._logger.info(
                f"✅ Камера підключена: {frame.shape[1]}x{frame.shape[0]}"
            )
            return True

        except Exception as e:
            self._logger.error(f"Помилка підключення: {e}")
            return False

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Отримання кадру"""
        if not self.is_connected():
            return False, None

        try:
            ret, frame = self._capture.read()
            return ret, frame if ret else None
        except Exception as e:
            self._logger.error(f"Помилка отримання кадру: {e}")
            return False, None

    def disconnect(self):
        """Відключення від камери"""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            self._logger.info("Камера відключена")

    def is_connected(self) -> bool:
        """Перевірка з'єднання"""
        return self._capture is not None and self._capture.isOpened()
