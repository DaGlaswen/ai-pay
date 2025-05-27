from datetime import datetime
from typing import Dict, Any, Optional

# Хранилище заказов (в продакшене использовать Redis или базу данных)
orders_storage: Dict[str, Dict[str, Any]] = {}


class OrderManager:
    """Менеджер заказов"""

    @staticmethod
    def generate_order_id() -> str:
        """Генерация уникального ID заказа"""
        return f"order_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    @staticmethod
    def save_order(order_id: str, data: Dict[str, Any]):
        """Сохранение заказа"""
        orders_storage[order_id] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    @staticmethod
    def get_order(order_id: str) -> Optional[Dict[str, Any]]:
        """Получение заказа"""
        return orders_storage.get(order_id)

    @staticmethod
    def update_order_status(order_id: str, status: str, additional_data: Dict[str, Any] = None):
        """Обновление статуса заказа"""
        if order_id in orders_storage:
            orders_storage[order_id]["status"] = status
            orders_storage[order_id]["updated_at"] = datetime.now().isoformat()
            if additional_data:
                orders_storage[order_id].update(additional_data)


order_manager = OrderManager()
