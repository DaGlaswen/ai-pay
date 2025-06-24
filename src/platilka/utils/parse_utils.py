import json
import re
from typing import Dict, Any, Optional

from platilka.exceptions.core_exceptions import InvalidAgentResponse


def parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
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


def extract_numeric_value(text: str, default: float = 0.0) -> float:
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
