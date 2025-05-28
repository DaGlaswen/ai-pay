class CheckoutException(Exception):
    """Ошибка при попытке обработать запрос на checkout"""
    pass

class InvalidAgentResponse(Exception):
    """Кастомная ошибка для случаев, когда browser-use не удалось извлечь структурированный ответ"""
    pass