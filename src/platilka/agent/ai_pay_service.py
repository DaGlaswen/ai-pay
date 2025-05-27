import json
import re
from typing import Dict, Any, Optional

from loguru import logger

from platilka.agent.agent_factory import AgentFactory


class AIPayService:
    """Расширенный класс для автоматизации покупок с детальной обработкой результатов"""

    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory

    def parse_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Извлечение JSON из текста ответа агента"""
        try:
            # Поиск JSON блока в тексте
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)

            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

            # Если JSON не найден, пытаемся парсить весь текст
            return json.loads(text)

        except Exception as e:
            logger.warning(f"Не удалось извлечь JSON из ответа: {str(e)}")
            return None

    def extract_numeric_value(self, text: str, default: float = 0.0) -> float:
        """Извлечение числового значения из строки"""
        try:
            # Ищем числа с возможными разделителями
            number_pattern = r'[\d\s,.]+'
            matches = re.findall(number_pattern, str(text))

            if matches:
                # Берем последнее найденное число (обычно цена)
                number_str = matches[-1].replace(' ', '').replace(',', '.')
                return float(number_str)

            return default
        except:
            return default

    async def checkout(self, product_url: str, quantity: int, delivery_info: Dict[str, Any]) -> Dict[
        str, Any]:
        """Детальное создание корзины с обработкой результатов"""
        try:

            # Создаем детальный промпт на русском языке
            checkout_prompt = f"""
            Ты - опытный автоматизатор покупок в интернет-магазинах. Твоя задача выполнить следующие шаги:

            ЭТАП 1: АНАЛИЗ ТОВАРА
            1. Перейди по ссылке: {product_url}
            2. Дождись полной загрузки страницы
            3. Внимательно изучи страницу товара и найди:
               - Точное название товара
               - Цену за единицу товара (в рублях)
               - Информацию о наличии товара
               - Максимальное доступное количество для заказа

            ЭТАП 2: ДОБАВЛЕНИЕ В КОРЗИНУ
            1. Нажми кнопку "Добавить в корзину"/"Купить" или аналогичную
            2. Перейди в корзину
            3. Найди поле для выбора количества товара
            4. Установи количество: {quantity} штук
            5. Если доступно меньше чем {quantity}, установи максимально возможное
            6. Нажми кнопку "Добавить в корзину" или аналогичную
            7. Подтверди добавление товара в корзину

            ЭТАП 3: ОФОРМЛЕНИЕ ЗАКАЗА
            1. Перейди к оформлению заказа (корзина -> оформить заказ)
            2. Заполни форму доставки:
               - Адрес доставки: {delivery_info.get('address', '')}
               - Предпочтительная дата: {delivery_info.get('preferred_date', 'Любая доступная')}
            3. Заполни контактные данные:
               - Телефон: phone_number
               - Email: email
               - ФИО: full_name

            ЭТАП 4: ВЫБОР ДОСТАВКИ
            1. Изучи доступные варианты доставки
            2. Выбери наиболее подходящий вариант
            3. Запомни стоимость и сроки доставки

            ЭТАП 5: СБОР ИНФОРМАЦИИ
            Собери всю информацию о заказе и верни в следующем JSON формате:
            {{
                "success": true/false,
                "product_name": "точное название товара",
                "product_price": число_цена_за_единицу,
                "requested_quantity": {quantity},
                "actual_quantity": фактическое_количество_в_корзине,
                "max_available_quantity": максимальное_доступное_количество_или_null,
                "availability_status": "в наличии/ограниченное количество/нет в наличии",
                "delivery_method": "название способа доставки",
                "delivery_cost": число_стоимость_доставки,
                "estimated_delivery_date": "дата или период доставки",
                "subtotal": число_стоимость_товаров,
                "total_price": число_общая_стоимость_включая_доставку,
                "currency": "RUB",
                "notes": "дополнительные заметки если есть",
                "error_message": "сообщение об ошибке если что-то не удалось"
            }}

            ВАЖНО: 
            - НЕ ПРОИЗВОДИ ОПЛАТУ! Остановись на этапе выбора способа оплаты
            - Если что-то не получается, продолжай попытки с альтернативными элементами
            - Будь внимателен к всплывающим окнам и уведомлениям
            - Сохрани состояние страницы для последующего подтверждения заказа
            """

            checkout_agent = await self.agent_factory.create_agent(checkout_prompt)
            logger.info(f"Начинаю создание корзины для {product_url}")
            result = await checkout_agent.run()

            # Извлекаем структурированные данные из ответа
            parsed_data = self.parse_json_from_text(str(result))

            if not parsed_data:
                # Если JSON не извлечен, создаем базовую структуру на основе текста
                logger.warning("Не удалось извлечь JSON из ответа агента, создаю базовую структуру")
                parsed_data = {
                    "success": True,
                    "product_name": "Товар",
                    "product_price": self.extract_numeric_value(str(result)),
                    "requested_quantity": quantity,
                    "actual_quantity": quantity,
                    "max_available_quantity": None,
                    "availability_status": "в наличии",
                    "delivery_method": "Стандартная доставка",
                    "delivery_cost": 0.0,
                    "estimated_delivery_date": "3-5 дней",
                    "subtotal": 0.0,
                    "total_price": 0.0,
                    "currency": "RUB",
                    "notes": "Данные извлечены автоматически",
                    "error_message": None
                }

            # Вычисляем totals если они не заполнены
            if parsed_data.get("subtotal", 0) == 0:
                parsed_data["subtotal"] = parsed_data.get("product_price", 0) * parsed_data.get("actual_quantity", 0)

            if parsed_data.get("total_price", 0) == 0:
                parsed_data["total_price"] = parsed_data.get("subtotal", 0) + parsed_data.get("delivery_cost", 0)

            logger.info(f"Корзина создана успешно. Общая стоимость: {parsed_data.get('total_price', 0)} руб.")
            return parsed_data

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

    async def confirm_order(self, order_data: Dict[str, Any], expected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Детальное подтверждение заказа с валидацией"""
        try:

            # Создаем промпт для валидации и подтверждения
            confirm_prompt = f"""
            Ты находишься на странице оформления заказа. Твоя задача - подтвердить заказ с проверкой всех параметров.

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
            result = await confirm_order_agent.run(confirm_prompt)

            # Извлекаем результат
            parsed_data = self.parse_json_from_text(str(result))

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
