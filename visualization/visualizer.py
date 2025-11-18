import cv2
from datetime import datetime
from typing import Tuple
import numpy as np


class FrameVisualizer:
    """Клас для візуалізації кадрів"""

    @staticmethod
    def draw_roi(
        frame: np.ndarray, roi: Tuple[int, int, int, int], is_detected: bool
    ) -> np.ndarray:
        """Малювання ROI на кадрі"""
        display = frame.copy()
        x, y, w, h = roi
        color = (0, 255, 0) if is_detected else (0, 0, 255)
        cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
        return display

    @staticmethod
    def add_status_text(
        frame: np.ndarray, is_detected: bool, bright_pixels: int
    ) -> np.ndarray:
        """Додавання тексту зі статусом"""
        display = frame.copy()

        status = "LAMP ON" if is_detected else "LAMP OFF"
        color = (0, 255, 0) if is_detected else (0, 0, 255)

        cv2.putText(
            display, status, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3
        )
        cv2.putText(
            display,
            f"Bright pixels: {bright_pixels}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        cv2.putText(
            display,
            timestamp,
            (10, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

        return display

    @classmethod
    def visualize(
        cls,
        frame: np.ndarray,
        roi: Tuple[int, int, int, int],
        is_detected: bool,
        bright_pixels: int,
    ) -> np.ndarray:
        """Повна візуалізація"""
        display = cls.draw_roi(frame, roi, is_detected)
        display = cls.add_status_text(display, is_detected, bright_pixels)
        return display
