from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from platilka.models.common import ValidationError


class ConfirmResponse(BaseModel):
    """Ответ после подтверждения заказа"""
    success: bool = Field(..., description="Успешность операции")
    order_id: str = Field(..., description="ID заказа")
    validation_success: bool = Field(..., description="Успешность валидации")
    payment_success: bool = Field(..., description="Успешность оплаты")
    actual_total_price: float = Field(..., description="Фактическая общая стоимость")
    payment_status: str = Field(..., description="Статус оплаты")
    order_number: Optional[str] = Field(None, description="Номер заказа из магазина")
    transaction_id: Optional[str] = Field(None, description="ID транзакции")
    discrepancies: list[ValidationError] = Field(default=[], description="Список расхождений")
    message: str = Field(..., description="Сообщение о результате")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время подтверждения")

    model_config = ConfigDict(arbitrary_types_allowed=True)
