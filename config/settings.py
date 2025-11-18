from dataclasses import dataclass
from typing import Tuple
from enum import Enum


class GeneratorState(Enum):
    """Стани генератора"""

    UNKNOWN = "unknown"
    ON = "on"
    OFF = "off"


@dataclass
class CameraConfig:
    """Конфігурація камери"""

    username: str
    password: str
    ip: str
    port: int = 554
    stream_path: str = "play1.sdp"

    @property
    def url(self) -> str:
        """Повний URL камери"""
        return f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{self.stream_path}"


@dataclass
class DetectionConfig:
    """Конфігурація визначення"""

    roi: Tuple[int, int, int, int]  # x, y, width, height
    bright_threshold: int = 190
    min_bright_pixels: int = 20

    def validate(self):
        """Валідація параметрів"""
        x, y, w, h = self.roi
        if w <= 0 or h <= 0:
            raise ValueError("ROI width and height must be positive")
        if not 0 <= self.bright_threshold <= 255:
            raise ValueError("Brightness threshold must be between 0 and 255")
        if self.min_bright_pixels < 0:
            raise ValueError("Min bright pixels must be non-negative")


@dataclass
class TelegramConfig:
    """Конфігурація Telegram"""

    bot_token: str
    chat_id: str

    def validate(self):
        """Валідація конфігурації"""
        if not self.bot_token or self.bot_token == "YOUR_BOT_TOKEN_HERE":
            raise ValueError("Telegram bot token not configured")
        if not self.chat_id or self.chat_id == "YOUR_CHAT_ID_HERE":
            raise ValueError("Telegram chat ID not configured")


@dataclass
class MonitorConfig:
    """Загальна конфігурація моніторингу"""

    camera: CameraConfig
    detection: DetectionConfig
    telegram: TelegramConfig
    check_interval: int = 5
    reconnect_delay: int = 30
    snapshot_folder: str = "snapshots"
    log_folder: str = "logs"
