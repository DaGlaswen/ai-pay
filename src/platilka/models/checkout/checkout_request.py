from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from platilka.models.common import DeliveryInfo

# TODO - временно и оплата на этом этапе
class CheckoutRequest(BaseModel):
    """Запрос для создания корзины"""
    product_url: HttpUrl = Field(..., description="Ссылка на товар")
    quantity: int = Field(1, ge=1, description="Желаемое количество товара")
    delivery_info: DeliveryInfo = Field(..., description="Информация о доставке")
    notes: Optional[str] = Field(None, description="Дополнительные заметки")
    payment_method: str = Field("card", description="Метод оплаты") #TODO - временно здесь