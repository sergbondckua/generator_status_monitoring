import cv2
import logging
from typing import Tuple
import numpy as np

from interfaces.base import IDetector
from config.settings import DetectionConfig


class BrightSpotDetector(IDetector):
    """Детектор яскравих точок (для лампочок)"""

    def __init__(self, config: DetectionConfig):
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        config.validate()

    def detect(self, frame: np.ndarray) -> Tuple[bool, int]:
        """
        Визначення яскравої точки (лампочки)

        Returns:
            (is_detected, bright_pixels)
        """
        try:
            # Вирізаємо ROI
            roi_frame = self._extract_roi(frame)

            # Подвійна перевірка: grayscale + червоний канал
            gray_pixels = self._detect_in_grayscale(roi_frame)
            red_pixels = self._detect_in_red_channel(roi_frame)

            # Використовуємо максимум
            bright_pixels = max(gray_pixels, red_pixels)
            is_detected = bright_pixels >= self._config.min_bright_pixels

            self._logger.debug(
                f"Gray: {gray_pixels}, Red: {red_pixels}, "
                f"Total: {bright_pixels}, Detected: {is_detected}"
            )

            return is_detected, bright_pixels

        except Exception as e:
            self._logger.error(f"Помилка детекції: {e}")
            return False, 0

    def _extract_roi(self, frame: np.ndarray) -> np.ndarray:
        """Вирізання ROI з кадру"""
        x, y, w, h = self._config.roi
        return frame[y : y + h, x : x + w]

    def _detect_in_grayscale(self, roi: np.ndarray) -> int:
        """Визначення в grayscale"""
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        _, mask = cv2.threshold(
            gray, self._config.bright_threshold, 255, cv2.THRESH_BINARY
        )
        return cv2.countNonZero(mask)

    def _detect_in_red_channel(self, roi: np.ndarray) -> int:
        """Визначення в червоному каналі"""
        if len(roi.shape) != 3:
            return 0

        b, g, r = cv2.split(roi)
        _, mask = cv2.threshold(
            r, self._config.bright_threshold - 50, 255, cv2.THRESH_BINARY
        )
        return cv2.countNonZero(mask)

    @property
    def roi(self) -> Tuple[int, int, int, int]:
        """Отримання ROI"""
        return self._config.roi
