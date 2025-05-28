from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from platilka.models.common import DeliveryDetails, ProductInfo, DeliveryInfo


class ConfirmRequest(BaseModel):
    """Запрос для подтверждения заказа"""
    product_url: HttpUrl = Field(..., description="Ссылка на товар")
    quantity: int = Field(1, ge=1, description="Желаемое количество товара")
    delivery_info: DeliveryInfo = Field(..., description="Информация о доставке")
    notes: Optional[str] = Field(None, description="Дополнительные заметки")
    order_id: str = Field(..., description="ID заказа из checkout")
    product: ProductInfo = Field(..., description="Ожидаемая информация о товаре")
    delivery: DeliveryDetails = Field(..., description="Ожидаемые детали доставки")
    # subtotal: Optional[float] = Field(..., description="Ожидаемая стоимость товаров")
    total_price: float = Field(..., description="Ожидаемая общая стоимость")
    payment_method: str = Field("card", description="Метод оплаты")
    validation_tolerance: float = Field(0.01, description="Допустимая погрешность для валидации цен")