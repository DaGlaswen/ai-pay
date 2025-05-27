import os

from platilka.core.config import config
from platilka.core.logging import logger

if __name__ == "__main__":
    import uvicorn

    # Проверяем наличие API ключа
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY не установлен в переменных окружения")
        exit(1)

    logger.info("Запуск сервиса автоматизации покупок...")
    uvicorn.run(
        "platilka.api.api:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.APP_RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
