from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np


class ICamera(ABC):
    """Інтерфейс для камери"""

    @abstractmethod
    def connect(self) -> bool:
        """Підключення до камери"""
        pass

    @abstractmethod
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Отримання кадру"""
        pass

    @abstractmethod
    def disconnect(self):
        """Відключення від камери"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Перевірка з'єднання"""
        pass


class IDetector(ABC):
    """Інтерфейс для детектора"""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> Tuple[bool, int]:
        """
        Визначення стану

        Returns:
            (is_detected, confidence): виявлено та впевненість
        """
        pass


class INotifier(ABC):
    """Інтерфейс для системи сповіщень"""

    @abstractmethod
    def send_message(self, message: str) -> bool:
        """Відправка текстового повідомлення"""
        pass

    @abstractmethod
    def send_image(self, image: np.ndarray, caption: str) -> bool:
        """Відправка зображення"""
        pass
