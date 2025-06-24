from itertools import product

CART_ADDER_PROMPT = """
Задача - найти кнопку "Добавить в корзину" и корректно нажать её.

### ИНСТРУКЦИЯ:
1. **Найди кнопку добавления в корзину** (ищи: "Добавить в корзину", "Купить", "В корзину", "Add to cart").  
2. **Проверь активность кнопки**:  
   - Если кнопка серая/заблокирована ("Нет в наличии") → верни ошибку.  
   - Если кнопка активна → нажми её.  
3. **Дождись подтверждения** (ищи: всплывающее окно, изменение иконки корзины, сообщение "Товар добавлен").  

### ФОРМАТ ОТВЕТА:
```json
{
    "success": true/false,
    "action": "Товар добавлен в корзину",
    "error": "Описание ошибки (если есть)"
}
"""

# Промпт для извлечения информации о товаре со страницы
CART_NAVIGATOR_PROMPT = """
Задача - найти кнопку для перехода в корзину и нажать на нее.

### ИНСТРУКЦИЯ:
1. Найди элемент корзины - как правило, он в правом верхнем углу экрана
2. Нажми на него  
3. Подтверди успешный переход (проверь заголовок "Корзина" или наличие списка товаров).  

### ФОРМАТ ОТВЕТА:
```json
{
    "success": true/false,
    "page_loaded": true/false,
    "error": "Не удалось перейти в корзину (если есть)"
}
"""

# Промпт для оценки товара на соответствие запросу пользователя
QUANTITY_MANAGER_PROMPT = """
Задача - установить корректное количество товара в корзине для '{product_name}'. Действуй по шагам:

### ИНСТРУКЦИЯ:
1. Найди элемент управления количеством (поле ввода, кнопки +/- или выпадающий список)
2. Установи значение: {quantity}
   - Для поля ввода: очисти → введи число → Enter
   - Для кнопок: нажимай "+" или "-" нужное количество раз
3. Если запрошенное количество недоступно - установи максимально возможное
4. Проверь, что количество и цена обновились

### ФОРМАТ ОТВЕТА:
```json
{{
    "success": true/false,
    "set_quantity": фактическое_количество,
    "max_available": максимальное_доступное,
    "error": "описание проблемы (если есть)"
}}
"""

# Промпт для формирования окончательных рекомендаций
PRODUCT_ANALYZER_PROMPT = """
Задача - извлечь ключевую информацию со страницы товара.

### ИНСТРУКЦИЯ
1. Убедись, что текущая страница - это страница товара (должны быть: цена, кнопка покупки, описание)
2. Извлеки точные данные:
   - Название товара
   - Цена
   - Наличие (текст типа "В наличии", "Осталось X шт", "Под заказ")
3. Проверь активность кнопки добавления в корзину

### ФОРМАТ ОТВЕТА:
```json
{
    "product_name": "название",
    "product_price": 9999,
    "availability": "статус",
    "is_available": true/false,
    "error": "описание проблемы (если есть)"
}
"""

CART_VERIFICATION_PROMPT = """
Задача - провалидировать корзину с товарами

### ИНСТРУКЦИЯ:
1. Убедись, что текущая страница - это корзина (ищи заголовок "Корзина", "Shopping Cart")
2. Проверь содержимое корзины:
   - Должен быть ровно 1 товар
   - Его название должно соответствовать: "{expected_product_name}"
   - Цена должна быть: {expected_price}
3. Если есть посторонние товары - удали их из корзины и проведи проверку заново

### ФОРМАТ ОТВЕТА:
```json
{{
    "is_cart_page": true/false,
    "product_match": true/false,
    "items_count": 1,
    "total_correct": true/false,
    "error": "найденные расхождения"
}}
"""


CHECKOUT_PROCESSOR_PROMPT = """
Ты - эксперт по оформлению заказов. Заполняй данные точно и аккуратно.

ИНСТРУКЦИЯ:
1. Нажми кнопку оформления ("Оформить заказ", "Checkout")
2. Заполни данные:
   - Способ доставки: "{delivery_method}"
   - Адрес: "{address}"
   - Контактные данные (телефон, email, ФИО)
3. Добавь комментарий: "{notes}"
4. Проверь все данные перед подтверждением

ФОРМАТ ОТВЕТА:
```json
{{
    "delivery_method": "способ",
    "delivery_cost": 500,
    "estimated_date": "дата",
    "contact_info_verified": true/false,
    "error": "описание проблемы"
}}
"""

PAYMENT_HANDLER_PROMPT = """
Ты - специалист по обработке платежей. Будь предельно внимателен с данными карт.

ИНСТРУКЦИЯ:
1. Выбери способ оплаты: {payment_method}
2. Для карт:
   - Введи номер: {card_number}
   - Срок: {expiration}
   - CVV: {cvv}
   - Держатель: {cardholder}
3. Подтверди платеж
4. Сохрани номер заказа

ФОРМАТ ОТВЕТА:
```json
{{
    "payment_success": true/false,
    "order_number": "12345",
    "payment_method": "способ",
    "error": "описание проблемы"
}}
"""

def get_cart_adder_prompt() -> str:
    """
    Формирует промпт для генерации поискового запроса

    Args:
        request: Запрос пользователя

    Returns:
        Промпт для генерации поискового запроса
    """
    return CART_ADDER_PROMPT

def get_cart_navigator_prompt() -> str:
    """
    Формирует промпт для навигации по корзине

    Returns:
        Промпт для перехода в корзину
    """
    return CART_NAVIGATOR_PROMPT

def get_cart_verification_prompt(expected_product_name: str, expected_price: float) -> str:

    return CART_VERIFICATION_PROMPT.format(expected_product_name=expected_product_name, expected_price=expected_price)

def get_quantity_manager_prompt(product_name: str, quantity: int) -> str:
    """
    Формирует промпт для управления количеством товара в корзине

    Args:
        quantity: Желаемое количество товара
        product_name: Название товара

    Returns:
        Промпт для изменения количества товара
    """
    return QUANTITY_MANAGER_PROMPT.format(product_name=product_name, quantity=quantity)


def get_product_analyzer_prompt() -> str:
    """
    Формирует промпт для анализа товара и оформления заказа

    """
    return PRODUCT_ANALYZER_PROMPT


def get_checkout_processor_prompt(delivery_method: str, address: str, notes: str) -> str:
    """
    Формирует промпт для обработки оформления заказа

    Args:
        delivery_method: Способ доставки
        address: Адрес доставки
        notes: Комментарий к заказу

    Returns:
        Промпт для оформления заказа
    """
    return CHECKOUT_PROCESSOR_PROMPT.format(
        delivery_method=delivery_method,
        address=address,
        notes=notes
    )


def get_payment_handler_prompt(
    payment_method: str,
    card_number: str = "",
    expiration: str = "",
    cvv: str = "",
    cardholder: str = ""
) -> str:
    """
    Формирует промпт для обработки платежа

    Args:
        payment_method: Способ оплаты
        card_number: Номер карты (если требуется)
        expiration: Срок действия карты (если требуется)
        cvv: CVV код (если требуется)
        cardholder: Держатель карты (если требуется)

    Returns:
        Промпт для обработки платежа
    """
    return PAYMENT_HANDLER_PROMPT.format(
        payment_method=payment_method,
        card_number=card_number,
        expiration=expiration,
        cvv=cvv,
        cardholder=cardholder
    )