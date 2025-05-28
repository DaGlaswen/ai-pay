import os
from contextlib import asynccontextmanager
from datetime import datetime
from locale import currency

from fastapi import FastAPI, APIRouter
from fastapi import HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from patchright.async_api import async_playwright as async_patchright

from platilka.agent.agent_factory import AgentFactory
from platilka.agent.ai_pay_service import AIPayService
from platilka.core.config import config
from platilka.core.logging import logger
from platilka.core.order_manager import orders_storage, order_manager
from platilka.models.checkout.checkout_request import CheckoutRequest
from platilka.models.checkout.checkout_response import CheckoutResponse
from platilka.models.common import ProductInfo, DeliveryDetails, ValidationError
from platilka.models.confirm.confirm_request import ConfirmRequest
from platilka.models.confirm.confirm_response import ConfirmResponse

# Создаем роутер
router = APIRouter()

# Глобальный объект агента
agent_factory: AgentFactory

ai_pay_service: AIPayService


# Инициализируем FastAPI приложение
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global agent_factory
    global ai_pay_service

    # Инициализация при запуске
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY не установлен в переменных окружения")

    # patchright = await async_patchright().start()
    agent_factory = AgentFactory(groq_api_key,
                                 # patchright
                                 )
    ai_pay_service = AIPayService(agent_factory)
    logger.info("Сервис автоматизации покупок запущен")

    yield

    # Очистка при завершении
    if agent_factory:
        await agent_factory.cleanup()
    logger.info("Сервис автоматизации покупок остановлен")


app = FastAPI(
    title=config.PROJECT_NAME,
    openapi_url=f"{config.API_V1_STR}/openapi.json",
    docs_url=f"{config.API_V1_STR}/docs",
    redoc_url=f"{config.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем основной роутер
api_router = APIRouter()

# Добавляем роутеры для различных эндпоинтов
api_router.include_router(
    api_router,
    prefix="/pay",
    tags=["pay"],
)

# Подключаем основной роутер к приложению
app.include_router(api_router, prefix=config.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    """Корневой эндпоинт с информацией о сервисе"""
    return {
        "name": config.PROJECT_NAME,
        "version": "0.1.0",
        "description": "Сервис AI-empowered оформления товаров в интернет-магазинах",
        "docs_url": f"{config.API_V1_STR}/docs",
    }


@app.post("/checkout", response_model=CheckoutResponse)
async def checkout_endpoint(request: CheckoutRequest, background_tasks: BackgroundTasks):
    """
    Эндпоинт для создания корзины и сбора информации о заказе

    Принимает ссылку на товар и информацию о доставке,
    возвращает детальную информацию о заказе без оплаты
    """
    try:
        global ai_pay_service

        if not ai_pay_service:
            raise HTTPException(status_code=500, detail="Сервис автоматизации не инициализирован")

        # Генерируем ID заказа
        order_id = order_manager.generate_order_id()

        logger.info(f"Начинаю создание корзины для заказа {order_id}")
        logger.info(f"URL товара: {request.product_url}")
        logger.info(f"Количество: {request.quantity}")

        # Вызываем детальное создание корзины
        checkout_result = await ai_pay_service.checkout(
            product_url=str(request.product_url),
            quantity=request.quantity,
            delivery_info=request.delivery_info.model_dump(),
            notes=request.notes
        )

        if not checkout_result.get("success", False):
            error_message = checkout_result.get("error_message", "Неизвестная ошибка при создании корзины")
            logger.error(f"Ошибка создания корзины для заказа {order_id}: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)

        # Создаем объекты ответа
        product_info = ProductInfo(
            name=checkout_result.get("product_name", "Неизвестный товар"),
            price=checkout_result.get("product_price", 0.0),
            quantity=checkout_result.get("actual_quantity", 0),
            availability=checkout_result.get("availability_status") != "нет в наличии",
            currency=checkout_result.get("currency"),
            # max_available_quantity=checkout_result.get("max_available_quantity", 0.0), #TODO хендлдить
            # availability_status=checkout_result.get("availability_status", "неизвестно")
        )

        delivery_details = DeliveryDetails(
            cost=checkout_result.get("delivery_cost", 0.0),
            estimated_date=checkout_result.get("estimated_delivery_date"),
            method=checkout_result.get("delivery_method", "Стандартная доставка"),
            address=request.delivery_info.address
        )

        # Собираем предупреждения
        warnings = []
        if checkout_result.get("requested_quantity", 0) != checkout_result.get("actual_quantity", 0):
            warnings.append(
                f"Запрошено {checkout_result.get('requested_quantity')} шт., добавлено {checkout_result.get('actual_quantity')} шт.")

        response = CheckoutResponse(
            order_id=order_id,
            success=True,
            product=product_info,
            delivery=delivery_details,
            subtotal=checkout_result.get("subtotal", 0.0),
            total_price=checkout_result.get("total_price", 0.0),
            notes=checkout_result.get("notes"),
            availability_status=checkout_result.get("availability_status"),
            warnings=warnings
        )

        # Сохраняем заказ
        order_manager.save_order(order_id, {
            "checkout_request": request.model_dump(),
            "checkout_response": response.model_dump(),
            "checkout_raw_data": checkout_result,
            "status": "checkout_completed"
        })

        logger.info(f"Корзина успешно создана для заказа {order_id}. Сумма: {response.total_price} {response.currency}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка в checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.post("/confirm", response_model=ConfirmResponse)
async def confirm_endpoint(request: ConfirmRequest):
    """
    Эндпоинт для подтверждения и оплаты заказа

    Валидирует информацию о заказе и производит оплату
    """
    try:
        global ai_pay_service

        if not ai_pay_service:
            raise HTTPException(status_code=500, detail="Сервис автоматизации не инициализирован")

        # Проверяем существование заказа
        # TODO допилить логику с order_data
        order_data = order_manager.get_order(request.order_id)
        if not order_data:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        logger.info(f"Начинаю подтверждение заказа {request.order_id}")

        # Подготавливаем данные для валидации
        expected_data = {
            "product_name": request.product.name,
            "quantity": request.product.quantity,
            "product_price": request.product.price,
            "delivery_cost": request.delivery.cost,
            "total_price": request.total_price,
            "delivery_method": request.delivery.method,
            "payment_method": request.payment_method
        }

        # Вызываем детальное подтверждение заказа
        confirm_result = await ai_pay_service.confirm_order(
            order_data=order_data,
            expected_data=expected_data
        )

        # Обрабатываем ошибки валидации
        validation_errors = []
        if not confirm_result.get("validation_success", False):
            raw_errors = confirm_result.get("validation_errors", [])
            for error in raw_errors:
                if isinstance(error, str):
                    validation_errors.append(ValidationError(
                        field="general",
                        expected="",
                        actual="",
                        message=error
                    ))

        # Определяем статус операции
        success = confirm_result.get("payment_success", False) and confirm_result.get("validation_success", False)
        status_message = "Заказ успешно подтвержден и оплачен"

        if not confirm_result.get("validation_success", False):
            status_message = "Ошибка валидации заказа"
        elif not confirm_result.get("payment_success", False):
            status_message = f"Ошибка оплаты: {confirm_result.get('payment_error', 'Неизвестная ошибка')}"

        response = ConfirmResponse(
            success=success,
            order_id=request.order_id,
            validation_success=confirm_result.get("validation_success", False),
            validation_errors=validation_errors,
            actual_total_price=confirm_result.get("actual_total_price", 0.0),
            payment_status=confirm_result.get("status", "failed"),
            order_number=confirm_result.get("order_number"),
            message=status_message
        )

        # Обновляем статус заказа
        order_manager.update_order_status(request.order_id, response.payment_status, {
            "confirm_request": request.model_dump(),
            "confirm_response": response.model_dump(),
            "confirm_raw_data": confirm_result
        })

        logger.info(f"Подтверждение заказа {request.order_id} завершено. Статус: {response.payment_status}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка в confirm: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/orders/{order_id}")
async def get_order_status(order_id: str):
    """Получить детальную информацию о заказе"""
    order_data = order_manager.get_order(order_id)
    if not order_data:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    return {
        "order_id": order_id,
        "status": order_data.get("status", "unknown"),
        "created_at": order_data.get("created_at"),
        "updated_at": order_data.get("updated_at"),
        "checkout_data": order_data.get("checkout_response"),
        "confirm_data": order_data.get("confirm_response")
    }


@app.get("/orders")
async def list_orders(limit: int = 50, offset: int = 0):
    """Получить список всех заказов"""
    orders = list(orders_storage.items())[offset:offset + limit]
    return {
        "orders": [
            {
                "order_id": order_id,
                "status": data.get("status", "unknown"),
                "created_at": data.get("created_at"),
                "total_price": data.get("checkout_response", {}).get("total_price", 0)
            }
            for order_id, data in orders
        ],
        "total": len(orders_storage),
        "limit": limit,
        "offset": offset
    }


@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Отменить заказ"""
    if order_id not in orders_storage:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order_manager.update_order_status(order_id, "cancelled")
    logger.info(f"Заказ {order_id} отменен")

    return {"message": f"Заказ {order_id} успешно отменен"}


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    global agent_factory

    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "automation_ready": agent_factory is not None,
        "orders_count": len(orders_storage),
        "version": "2.0.0"
    }


@app.post("/cleanup")
async def cleanup_browser():
    """Очистка ресурсов браузера"""
    global agent_factory

    if agent_factory:
        await agent_factory.cleanup()
        agent_factory = None

    return {"message": "Браузер закрыт и ресурсы освобождены"}


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "orders_count": len(orders_storage),
        "browser_initialized": agent_factory is not None
    }


@app.get("/config")
async def get_config():
    """Получить текущую конфигурацию (без секретных данных)"""
    return {
        "default_phone": config.PHONE,
        "default_email": config.EMAIL,
        "default_name": config.FULL_NAME,
        "browser_headless": config.BROWSER_HEADLESS,
        "browser_timeout": config.BROWSER_TIMEOUT
    }
