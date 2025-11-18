import logging
import os


def setup_logging(
    log_folder: str = "logs", log_file: str = "generator_monitor.log"
):
    """Налаштування системи логування"""

    # Створюємо папку для логів
    os.makedirs(log_folder, exist_ok=True)

    log_path = os.path.join(log_folder, log_file)

    # Налаштування форматування
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("=" * 40)
    logging.info("Логування налаштовано")
    logging.info(f"Файл логів: {log_path}")
    logging.info("=" * 40)
