import sys
from loguru import logger

from platilka.core.config import config


def setup_logging():
    """Настраивает логирование для приложения"""
    # Удаляем стандартный обработчик
    logger.remove()

    # Добавляем обработчик с настройками форматирования
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=config.LOG_LEVEL,
        enqueue=True,
    )

    # Добавляем обработчик для сохранения логов в файл
    logger.add(
        "logs/platilka.log",
        rotation="10 MB",
        retention="1 week",
        level=config.LOG_LEVEL,
        enqueue=True,
    )

    return logger


# Создаем экземпляр логгера
logger = setup_logging()