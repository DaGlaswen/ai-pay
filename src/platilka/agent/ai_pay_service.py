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
            Ты - опытный автоматизатор покупок в интернет-магазинах. Твоя задача выполнить следующие шаги:

            ЭТАП 1: АНАЛИЗ ТОВАРА
            1. Перейди по ссылке: {product_url}
            2. Дождись полной загрузки страницы (включая все динамические элементы)
            3. Закрой всплывающие окна (cookies, промо, подписки), если появятся
            4. КРИТИЧНО: Убедись, что находишься на странице конкретного товара, а не в каталоге или на другой странице:
               - Проверь URL - он должен содержать идентификатор товара или его название
               - На странице должны присутствовать: детальные фото товара, описание, цена, кнопка "Добавить в корзину"
               - Если попал в каталог или на другую страницу - вернись на изначальную страницу
               - Если перенаправило на главную страницу - товар может быть недоступен, верни соответствующую ошибку
               
               После подтверждения нахождения на правильной странице товара, изучи и найди:
               - Точное название товара (обычно в заголовке H1, крупный шрифт вверху страницы)
               - Актуальную цену за единицу товара в рублях (учитывай скидки, акции, зачеркнутые старые цены)
               - Информацию о наличии товара и максимальном доступном количестве ("В наличии", "Осталось X штук", "Под заказ")
            НЕ ПЕРЕХОДИ В КАТАЛОГ ТОВАРОВ

            ЭТАП 2: ДОБАВЛЕНИЕ В КОРЗИНУ
            1. Найди и нажми кнопку добавления в корзину (варианты: "Добавить в корзину", "Купить", "В корзину", "Add to cart")
               В случае, если не можешь найти кнопку - верни ошибку с описанием доступных элементов
            2. Дождись подтверждения добавления (уведомление, изменение счетчика корзины)
            3. Найди кнопку для перехода в корзину (варианты: "Корзина", "Перейти в корзину", "Оформить", иконка корзины)
               В случае, если не можешь найти - верни ошибку
            4. Найди элемент для управления количеством товара. Ищи в следующем порядке:
               а) Поле ввода (input) с атрибутами type="number", name/id содержащими "quantity", "qty", "amount", "count"
               б) Выпадающий список (select/dropdown) для выбора количества
               в) Кнопки увеличения/уменьшения ("+"/"-", "плюс"/"минус", стрелки вверх/вниз)
               г) Спиннер (input с кнопками +/- рядом)
               д) Слайдер для выбора количества
            5. Проверь текущее значение в поле количества и ограничения:
               - Минимальное количество (обычно 1)
               - Максимальное доступное количество (если указано)
               - Шаг изменения (обычно 1)
            6. Установи количество: {quantity} штук используя наиболее подходящий метод:
               - Для input поля: очисти поле и введи нужное значение и нажми 'Enter' для применения
               - Для dropdown: выбери опцию с нужным количеством
               - Для кнопок +/-: нажимай нужное количество раз (если текущее значение меньше требуемого)
               - Для слайдера: перетащи на нужную позицию
            7. Если запрашиваемое количество {quantity} недоступно:
               - Установи максимально возможное количество из доступных вариантов
               - Запомни фактически установленное количество
               - Проверь появление предупреждений о лимитах количества
            8. Проверь правильность установленного количества:
               - Убедись, что в поле отображается нужное значение
               - Проверь, что не появилось сообщений об ошибках
               - При необходимости скорректируй количество повторно
            9. Собери всю необходимую информацию
            10. Прекрати взаимодействие со страницей, не нажимай никаких кнопок и не переходи никуда

            ЭТАП 3: ОФОРМЛЕНИЕ ЗАКАЗА
            1. Найди и нажми кнопку оформления заказа (варианты: "Оформить заказ", "Перейти к оформлению", "Checkout", "Продолжить")
            2. Выбери способ доставки: "{delivery_info.get('delivery_method', 'Курьерская доставка')}" или наиболее подходящий вариант
               Запомни стоимость и сроки выбранного способа доставки
            3. Заполни адрес доставки: {delivery_info.get('address', '')}
               Если есть выпадающие меню для города/региона - выбери соответствующие опции
            4. Укажи предпочтительную дату доставки: {delivery_info.get('preferred_date', 'Ближайшая доступная')}
            5. Заполни контактные данные, ищи поля по следующим критериям:
               а) ТЕЛЕФОН: phone_number
               - Варианты подписей: "Телефон", "Мобильный", "Контактный телефон", "Phone", "Mobile"
               - Учитывай маски ввода (+7, 8, скобки, дефисы)
               - Если поле имеет префикс "+7" или "8" - вводи номер без этих символов
               - Проверь правильность формата после ввода
               
               б) EMAIL: email
               - Ищи поля с атрибутами: name/id содержащими "email", "mail", "e-mail"
               - Варианты подписей: "Email", "Электронная почта", "E-mail", "Почта"
               - Убедись, что email проходит валидацию (нет сообщений об ошибке)
               
               в) ФИО: full_name
               - Ищи одно общее поле или разделенные поля для имени, фамилии, отчества
               - Варианты атрибутов: "name", "fullname", "fio", "firstname", "lastname", "surname"
               - Варианты подписей: "ФИО", "Имя", "Фамилия", "Полное имя", "Получатель", "Фамилия Имя Отчество"
               - Если поля разделены - распредели full_name по соответствующим полям
               - Формат: "Фамилия Имя Отчество" или "Имя Фамилия"
               
               г) ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ (если обязательны):
               - Способ связи: выбери "Телефон" если есть выбор
               - Согласие на обработку данных: отметь чекбоксы согласия, если они обязательны
            6. Заполни форму с комментарием к заказу следующим значением: '{notes}'
            7. Проверь правильность заполнения всех полей и итоговую стоимость.
            
            ЭТАП 4: ОПЛАТА (только если валидация прошла успешно)
            1. Выбери способ оплаты: {request.payment_method}
            2. Заполни данные карты:
               - Номер карты: card_number
               - Срок действия: card_expiration_date
               - CVV: card_cvv
               - Имя держателя: cardholder_name
            3. Подтверди оплату
            4. Дождись результата операции
            5. Сохрани номер заказа если он появился
            
            
            ЭТАП 5: СБОР ИНФОРМАЦИИ И ФОРМАТ ОТВЕТА
            Собери всю информацию и верни в формате JSON:
            Верни информацию в формате JSON:
            ```json
            {{
                "success": true/false,
                "product_name": "точное название товара",
                "product_price": цена_за_единицу_число,
                "requested_quantity": {quantity},
                "actual_quantity": фактическое_количество_в_корзине,
                "max_available_quantity": максимальное_доступное_количество_или_null,
                "availability_status": "в наличии/ограниченное количество/нет в наличии/под заказ",
                "delivery_method": "название выбранного способа доставки",
                "delivery_cost": стоимость_доставки_число,
                "estimated_delivery_date": "дата или период доставки",
                "subtotal": стоимость_товаров_без_доставки_число,
                "total_price": общая_стоимость_включая_доставку_число,
                "currency": "RUB",
                "notes": "дополнительные заметки если есть",
                "error_message": "подробное сообщение об ошибке если что-то не удалось"
            }}
            ```

            КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:
            - НЕ ПЕРЕХОДИ В КАТАЛОГ ТОВАРОВ
            - Если элемент не найден с первой попытки, ищи альтернативные селекторы и варианты названий
            - Обрабатывай все всплывающие окна и уведомления
            - При ошибках указывай конкретный этап и причину неудачи
            - Адаптируйся к особенностям интерфейса конкретного сайта
            - Возвращай максимально подробную информацию даже в случае частичного выполнения
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
