from pydantic import BaseModel, Field

from platilka.models.common import DeliveryDetails, ProductInfo


class ConfirmRequest(BaseModel):
    """Запрос для подтверждения заказа"""
    order_id: str = Field(..., description="ID заказа из checkout")
    product: ProductInfo = Field(..., description="Ожидаемая информация о товаре")
    delivery: DeliveryDetails = Field(..., description="Ожидаемые детали доставки")
    subtotal: float = Field(..., description="Ожидаемая стоимость товаров")
    total_price: float = Field(..., description="Ожидаемая общая стоимость")
    payment_method: str = Field("card", description="Метод оплаты")
    validation_tolerance: float = Field(0.01, description="Допустимая погрешность для валидации цен")