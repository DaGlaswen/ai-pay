import json
import re
from typing import Dict, Any, Optional

from loguru import logger

from platilka.agent.agent_factory import AgentFactory
from platilka.exceptions.core_exceptions import InvalidAgentResponse
from platilka.models.checkout.checkout_request import CheckoutRequest


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
            raise InvalidAgentResponse(f"Не удалось извлечь JSON из ответа: {str(e)}")

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

    async def checkout(self, product_url: str, quantity: int,
                       request: CheckoutRequest,
                       delivery_info: Dict[str, Any],
                       notes: str
                       ) -> Dict[
        str, Any]:
        """Детальное создание корзины с обработкой результатов"""
        try:

            # Создаем детальный промпт на русском языке
            checkout_prompt = f"""
            Ты - профессиональный автоматизатор покупок в интернет-магазинах. Выполняй следующие действия максимально точно и последовательно:
            
            === КРИТИЧЕСКИЕ ПРАВИЛА ===
            1. Работай ТОЛЬКО на странице товара - НЕ ПЕРЕХОДИ В КАТАЛОГ
            2. Все действия выполняй как реальный пользователь
            3. При ошибках указывай конкретный этап и детали проблемы
            4. Адаптируйся к интерфейсу сайта, но не отклоняйся от инструкции
            5. Не нажимай на кнопки и не заполняй формы слишком быстро
            
            ЭТАП 1: АНАЛИЗ ТОВАРА
            1. Перейди по ссылке: {product_url}
               - Убедись, что это страница товара (есть цена, кнопка "Купить")
               - Если это не товар - немедленно верни ошибку
            2. Найди и запиши:
               - Точное название товара (ищи в h1, product-title, item-name)
               - Цену (ищи в price-value, product-price, money-amount)
               - Статус наличия ("В наличии", "Осталось X шт", "Под заказ")
            
            ЭТАП 2: ДОБАВЛЕНИЕ В КОРЗИНУ
            1. Добавление товара:
               - Найди кнопку (ищи: "Добавить в корзину", "Купить", "В корзину", "Add to cart")
               - Если кнопка неактивна ("Нет в наличии") - верни ошибку
               - Нажми и дождись подтверждения (ищи изменения в иконке корзины или popup)
            2. Переход в корзину:
               - Найди элемент корзины (ищи: "Корзина", "Оформить", иконку корзины, "Cart")
               - Нажми и дождись загрузки страницы корзины
            
            ЭТАП 3: УПРАВЛЕНИЕ КОЛИЧЕСТВОМ
            1. Найди элемент управления количеством (приоритет поиска):
               а) Поле ввода (input[type='number'], [id*='quantity'], [name*='qty'])
               б) Выпадающий список (select)
               в) Кнопки +/- ("плюс", "минус", стрелки)
               г) Слайдер количества
            2. Проверь ограничения:
               - Минимум (обычно 1)
               - Максимум (если указан)
               - Шаг изменения (обычно 1)
            3. Установи количество {quantity}:
               - Для поля: очисти, введи значение, нажми Enter
               - Для dropdown: выбери значение
               - Для кнопок: нажимай нужное количество раз
               - Для слайдера: перетащи ползунок
            4. Если {quantity} недоступно:
               - Установи максимально возможное
               - Запомни фактическое количество
               - Проверь наличие предупреждений
            5. Валидация:
               - Убедись, что верное количество отображается
               - Проверь отсутствие ошибок
               - Запомни стоимость товаров
            
            ЭТАП 4: ОФОРМЛЕНИЕ ЗАКАЗА
            1. Нажми кнопку оформления (ищи: "Оформить заказ", "Checkout", "Продолжить")
            2. Заполни данные доставки:
               - Способ: "{delivery_info.get('delivery_method', 'Курьерская доставка')}"
               - Адрес: "{delivery_info.get('address', '')}"
               - Дата: "{delivery_info.get('preferred_date', 'Ближайшая доступная')}"
            3. Контактные данные:
               - Телефон: phone_number
               - Email: email
               - ФИО: full_name
            4. Комментарий: "{notes}" (если есть поле)
            5. Проверь все данные перед продолжением
            
            ЭТАП 5: ОПЛАТА (только после валидации)
            1. Выбери способ оплаты: {request.payment_method}
            2. Для карты:
               - Номер: card_number
               - Срок: card_expiration_date
               - CVV: card_cvv
               - Держатель: cardholder_name
            3. Подтверди оплату
            4. Сохрани номер заказа
            
            ФОРМАТ ОТВЕТА (сохранен исходный):
            ```json
            {{
                "success": true/false,
                "product_name": "название товара",
                "product_price": цена_за_единицу,
                "requested_quantity": {quantity},
                "actual_quantity": фактическое_количество,
                "max_available_quantity": максимальное_доступное,
                "availability_status": "в наличии/ограничено/нет",
                "delivery_method": "способ доставки",
                "delivery_cost": стоимость_доставки,
                "estimated_delivery_date": "дата доставки",
                "subtotal": стоимость_товаров,
                "total_price": общая_стоимость,
                "currency": "RUB",
                "notes": "{notes}",
                "error_message": "описание ошибки (если есть)"
            ```    
            }}
            """

            checkout_agent = await self.agent_factory.create_agent(checkout_prompt)
            logger.info(f"Начинаю создание корзины для {product_url}")
            result = await checkout_agent.run()

            extracted_content = result.history[-1].result[0].extracted_content

            # Извлекаем структурированные данные из ответа
            parsed_data = self.parse_json_from_text(str(extracted_content))

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
