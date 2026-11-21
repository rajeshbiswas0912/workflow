from fastapi import APIRouter

from app.controllers import (
    auth_controller,
    customer_controller,
    dashboard_controller,
    department_controller,
    employee_controller,
    order_controller,
    product_controller,
    report_controller,
    role_controller
)


api_router = APIRouter()
api_router.include_router(auth_controller.router)
api_router.include_router(employee_controller.router)
api_router.include_router(role_controller.router)
api_router.include_router(department_controller.router)
api_router.include_router(customer_controller.router)
api_router.include_router(product_controller.router)
api_router.include_router(order_controller.router)
api_router.include_router(dashboard_controller.router)
api_router.include_router(report_controller.router)
