from typing import Dict, Any

from loguru import logger

from platilka.agent.agent_factory import AgentFactory
from platilka.models.checkout.checkout_request import CheckoutRequest
from platilka.utils.parse_utils import parse_json_from_text
from platilka.utils.prompts import get_product_analyzer_prompt, get_cart_adder_prompt, get_quantity_manager_prompt, \
    get_checkout_processor_prompt, get_cart_navigator_prompt, get_cart_verification_prompt


class AIPayService:
    """Расширенный класс для автоматизации покупок с детальной обработкой результатов"""

    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory

    async def checkout(self, product_url: str, quantity: int,
                       request: CheckoutRequest,
                       delivery_info: Dict[str, Any],
                       notes: str
                       ) -> Dict[
        str, Any]:
        """Детальное создание корзины с обработкой результатов"""
        try:

            browser_session = self.agent_factory.browser_session
            product_page = await browser_session.create_new_tab(product_url)

            agent = await self.agent_factory.create_agent(get_product_analyzer_prompt(), product_page)
            result = await agent.run()
            product_data = await self._handle_agent_response(result)

            agent = await self.agent_factory.create_agent(get_cart_adder_prompt(), product_page)
            result = await agent.run()
            cart_adder_data = await self._handle_agent_response(result)

            agent = await self.agent_factory.create_agent(get_cart_navigator_prompt(), product_page)
            result = await agent.run()
            cart_navigator_data = await self._handle_agent_response(result)

            current_page = await browser_session.get_current_page()

            agent = await self.agent_factory.create_agent(
                get_cart_verification_prompt(product_data['product_name'], float(product_data['product_price'])), current_page)

            agent = await self.agent_factory.create_agent(get_quantity_manager_prompt(product_data['product_name'], request.quantity), current_page)
            result = await agent.run()
            quantity_data = await self._handle_agent_response(result)

            agent = await self.agent_factory.create_agent(
                get_checkout_processor_prompt(delivery_info.get('delivery_method', 'Курьерская доставка'),
                                              delivery_info.get('address', 'Курьерская доставка'),
                                              notes),
                current_page
            )
            result = await agent.run()
            checkout_data = await self._handle_agent_response(result)

            return checkout_data

        except Exception as e:
            logger.error(f"Ошибка при создании корзины: {str(e)}")
            return {
                "success": False,
                "error_message": str(e),
                "product_name": "",
                "product_price": 0.0,
                "requested_quantity": quantity,
                "actual_quantity": 0,
                "total_price": 0.0
            }

    async def _handle_agent_response(self, result):

        extracted_content = result.history[-1].result[0].extracted_content
        # Извлекаем структурированные данные из ответа
        parsed_data = parse_json_from_text(str(extracted_content))
        return parsed_data

    async def confirm_order(self, order_data: Dict[str, Any], expected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Детальное подтверждение заказа с валидацией"""
        try:

            # Создаем промпт для валидации и подтверждения
            confirm_prompt = f"""
            Твоя задача - подтвердить заказ с проверкой всех параметров.
            
            ЭТАП 1: 
            1. Перейди по ссылке: TODO заполнить позже
            2. Дождись полной загрузки страницы (включая все динамические элементы)
            3. Закрой всплывающие окна (cookies, промо, подписки), если появятся

            ЭТАП 1: ВАЛИДАЦИЯ ЗАКАЗА
            Проверь текущие параметры заказа на странице и сравни с ожидаемыми:

            ОЖИДАЕМЫЕ ПАРАМЕТРЫ:
            - Название товара: {expected_data.get('product_name', '')}
            - Количество: {expected_data.get('quantity', 0)} шт.
            - Цена за единицу: {expected_data.get('product_price', 0)} руб.
            - Стоимость доставки: {expected_data.get('delivery_cost', 0)} руб.
            - Общая стоимость: {expected_data.get('total_price', 0)} руб.
            - Способ доставки: {expected_data.get('delivery_method', '')}

            ЭТАП 2: ПРОВЕРКА РАСХОЖДЕНИЙ
            Если любой из параметров НЕ СОВПАДАЕТ:
            1. Зафиксируй все расхождения
            2. НЕ ПРОДОЛЖАЙ с оплатой
            3. Верни информацию об ошибках валидации

            ЭТАП 3: ОПЛАТА (только если валидация прошла успешно)
            1. Выбери способ оплаты: {expected_data.get('payment_method', 'card')}
            2. Заполни данные карты:
               - Номер карты: card_number
               - Срок действия: card_expiration_date
               - CVV: card_cvv
               - Имя держателя: cardholder_name
            3. Подтверди оплату
            4. Дождись результата операции
            5. Сохрани номер заказа если он появился

            ВЕРНИ РЕЗУЛЬТАТ В JSON ФОРМАТЕ:
            {{
                "validation_success": true/false,
                "validation_errors": ["список ошибок валидации"],
                "actual_product_name": "фактическое название товара",
                "actual_quantity": фактическое_количество,
                "actual_product_price": фактическая_цена_за_единицу,
                "actual_delivery_cost": фактическая_стоимость_доставки,
                "actual_total_price": фактическая_общая_стоимость,
                "payment_success": true/false,
                "payment_error": "ошибка оплаты если есть",
                "order_number": "номер заказа из магазина",
                "payment_confirmation": "подтверждение оплаты",
                "status": "confirmed/failed/validation_failed"
            }}

            ВАЖНО:
            - Будь очень внимателен к цифрам и ценам
            - Не игнорируй всплывающие окна с ошибками
            - Если валидация не прошла - сразу останавливайся
            """

            confirm_order_agent = await self.agent_factory.create_agent(confirm_prompt)
            logger.info("Начинаю подтверждение заказа с валидацией")
            result = await confirm_order_agent.run()

            # Извлекаем результат
            parsed_data = parse_json_from_text(str(result))

            if not parsed_data:
                logger.warning("Не удалось извлечь JSON из ответа подтверждения")
                parsed_data = {
                    "validation_success": False,
                    "validation_errors": ["Не удалось получить ответ от агента"],
                    "payment_success": False,
                    "status": "failed",
                    "actual_total_price": 0.0
                }

            # Проверяем валидацию
            if not parsed_data.get("validation_success", False):
                logger.error(f"Валидация не прошла: {parsed_data.get('validation_errors', [])}")
                parsed_data["status"] = "validation_failed"

            logger.info(f"Подтверждение заказа завершено со статусом: {parsed_data.get('status', 'unknown')}")
            return parsed_data

        except Exception as e:
            logger.error(f"Ошибка при подтверждении заказа: {str(e)}")
            return {
                "validation_success": False,
                "validation_errors": [str(e)],
                "payment_success": False,
                "status": "failed",
                "actual_total_price": 0.0,
                "payment_error": str(e)
            }

    def format_price(self, price: float) -> str:
        """Форматирование цены"""
        return f"{price:.2f} ₽"

    def validate_price_difference(self, expected: float, actual: float, tolerance: float = 0.01) -> bool:
        """Проверка разности цен с допустимым отклонением"""
        return abs(expected - actual) <= tolerance
