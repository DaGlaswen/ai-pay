from browser_use import Agent, Browser, BrowserConfig, BrowserContextConfig
from langchain_groq import ChatGroq
from loguru import logger

from platilka.core.config import config, sensitive_data


class AgentFactory:
    """Расширенный класс для автоматизации покупок с детальной обработкой результатов"""

    def __init__(self, groq_api_key: str,
                 # patchright
                 ):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=config.LLM_MODEL_NAME,
            temperature=config.LLM_TEMPERATURE,
        )
        # TODO вернуть новую версию
        # self.browser_session = BrowserSession(
        #     # playwright=patchright,
        #     # user_data_dir='~/.config/browseruse/profiles/stealth',
        #     headless=False,
        #     disable_security=False,
        #     # deterministic_rendering=False,
        # )
        self.browser_session = Browser(
            config=BrowserConfig(
                headless=False,
                disable_security=False,
                # keep_alive=True,
                new_context_config=BrowserContextConfig(
                    # keep_alive=True,
                    disable_security=False,
                ),
            )
        )

    async def create_agent(self, task: str):
        """Инициализация браузерного агента"""
        try:
            agent = Agent(
                llm=self.llm,
                browser_session=self.browser_session,
                sensitive_data=sensitive_data,
                task=task,
            )
            logger.info("Браузерный агент успешно инициализирован")
            return agent
        except Exception as e:
            logger.error(f"Ошибка инициализации агента: {str(e)}")
            raise

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.browser_session.stop()
            logger.info("Процесс браузера был убит")
        except Exception as e:
            logger.warning(f"Ошибка при остановке процесса браузера: {str(e)}")
