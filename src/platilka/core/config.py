import os

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


# Конфигурация
class Config:
    """Конфигурация приложения"""

    # Настройки браузера
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))

    APP_HOST: str = "localhost"
    APP_PORT: int = 8001
    APP_RELOAD: bool = True

    # Настройки LLM
    LLM_MODEL_NAME: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    LLM_TEMPERATURE: float = 0.0

    # Логирование
    LOG_LEVEL: str = "DEBUG"

    PROJECT_NAME: str = "Сервис AI-empowered оформления товаров в интернет-магазинах"
    API_V1_STR: str = "/api/v1"

config = Config()
sensitive_data = {
    # Данные карты (в продакшене использовать безопасное хранение)
    "card_number": os.getenv("CARD_NUMBER", "4111111111111111"),
    "card_expiry": os.getenv("CARD_EXPIRY", "12/25"),
    "card_cvv": os.getenv("CARD_CVV", "123"),
    "cardholder_name": os.getenv("CARDHOLDER_NAME", "Test User"),
    # Персональные данные
    "phone_number": os.getenv("DEFAULT_PHONE", "+79671717955"),
    "email": os.getenv("DEFAULT_EMAIL", "test@example.com"),
    "full_name": os.getenv("DEFAULT_FULL_NAME", "Головинов Данил Алексеевич")
}
