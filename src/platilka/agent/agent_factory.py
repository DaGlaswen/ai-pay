from browser_use import Agent
from browser_use.browser.session import BrowserSession, BrowserProfile
from langchain_groq import ChatGroq
from loguru import logger
from playwright.async_api import Page

from platilka.core.config import config, sensitive_data


class AgentFactory:
    """Расширенный класс для автоматизации покупок с детальной обработкой результатов"""

    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=config.LLM_MODEL_NAME,
            temperature=config.LLM_TEMPERATURE,
        )
        self.browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                window_size={'width': 1280, 'height': 1024},
                keep_alive=True,
                disable_security=True,
                user_data_dir=None,
                slow_mo=2000
            )
        )

    async def create_agent(self, task: str, page: Page = None) -> Agent:
        """Инициализация браузерного агента"""
        try:
            agent = Agent(
                llm=self.llm,
                browser_session=self.browser_session,
                page=page,
                sensitive_data=sensitive_data,
                task=task,
            )
            logger.info("Браузерный агент успешно инициализирован")
            return agent
        except Exception as e:
            logger.error(f"Ошибка инициализации агента: {str(e)}")
            raise

    async def start_browser(self):
        try:
            await self.browser_session.start()
            logger.info("Процесс браузера был запущен")
        except Exception as e:
            logger.error(f"Ошибка при попытке старта процесса браузера: {str(e)}")

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.browser_session.close()
            logger.info("Процесс браузера был убит")
        except Exception as e:
            logger.warning(f"Ошибка при остановке процесса браузера: {str(e)}")
