from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict


# Модели данных
class DeliveryInfo(BaseModel):
    """Информация о доставке"""
    address: str = Field(..., description="Полный адрес доставки")
    preferred_date: Optional[str] = Field(None, description="Предпочтительная дата доставки (DD.MM.YYYY)")
    delivery_method: Optional[str] = Field(None, description="Предпочтительный метод доставки")
    recipient_name: Optional[str] = Field(None, description="Имя получателя")
    phone: Optional[str] = Field(None, description="Телефон получателя")

class ProductInfo(BaseModel):
    """Информация о товаре"""
    name: str = Field(..., description="Название товара")
    price: float = Field(..., description="Цена за единицу")
    quantity: int = Field(..., description="Количество")
    availability: bool = Field(..., description="Доступность товара")
    max_available_quantity: Optional[int] = Field(None, description="Максимальное доступное количество")
    currency: str = Field("RUB", description="Валюта")

class DeliveryDetails(BaseModel):
    """Детали доставки"""
    cost: float = Field(..., description="Стоимость доставки")
    estimated_date: Optional[str] = Field(None, description="Ожидаемая дата доставки")
    method: str = Field(..., description="Способ доставки")
    estimated_time: Optional[str] = Field(None, description="Ожидаемое время доставки")

class ValidationError(BaseModel):
    """Ошибка валидации"""
    field: str = Field(..., description="Поле с ошибкой")
    expected: str | int | float = Field(..., description="Ожидаемое значение")
    actual: str | int | float= Field(..., description="Фактическое значение")
    message: str = Field(..., description="Описание ошибки")

    model_config = ConfigDict(arbitrary_types_allowed=True) # TODO пофиксить
