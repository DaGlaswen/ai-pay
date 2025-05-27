from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from platilka.models.common import DeliveryDetails, ProductInfo


class CheckoutResponse(BaseModel):
    """Ответ с информацией о корзине"""
    order_id: str = Field(..., description="Уникальный ID заказа")
    success: bool = Field(..., description="Успешность операции")
    product: ProductInfo = Field(..., description="Информация о товаре")
    delivery: DeliveryDetails = Field(..., description="Детали доставки")
    subtotal: float = Field(..., description="Стоимость товаров без доставки")
    total_price: float = Field(..., description="Общая стоимость заказа")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания корзины")
    availability_status: str = Field(..., description="Статус наличия товара")
    notes: Optional[str] = Field(None, description="Дополнительные заметки")
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")