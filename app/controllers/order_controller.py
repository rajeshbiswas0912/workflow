from datetime import date

from fastapi import APIRouter, Depends, Query

from app.enums.order import OrderStatus
from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.employee import EmployeeResponse
from app.schemas.order import OrderCreate, OrderDetail, OrderItemUpdate, OrderPage, OrderStatusUpdate, OrderUpdate
from app.schemas.order_item import OrderItemCreate
from app.services.order_service import OrderService
from app.utils.dependencies import get_order_service, require_permission

router = APIRouter(prefix="/orders", tags=["Orders"])

ORD_VIEW = Depends(require_permission(PermissionArea.orders, PermissionLevel.view))
ORD_EDIT_GUARD = require_permission(PermissionArea.orders, PermissionLevel.edit)
ORD_EDIT = Depends(ORD_EDIT_GUARD)
ORD_FULL = Depends(require_permission(PermissionArea.orders, PermissionLevel.full))


@router.get("", response_model=ApiResponse[OrderPage], dependencies=[ORD_VIEW],
            summary="List orders with status chip counts")
def list_orders(
    search: str | None = None,
    customer_id: int | None = None,
    handled_by_id: int | None = None,
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_deleted: bool = False,
    limit: int = Query(8, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: OrderService = Depends(get_order_service),
):
    return ApiResponse(
        data=service.list_orders(search, customer_id, handled_by_id, status, date_from, date_to,
                                 include_deleted, limit, offset),
        message="Orders fetched",
    )


@router.get("/by-number", response_model=ApiResponse[OrderDetail], dependencies=[ORD_VIEW])
def get_order_by_number(order_number: str, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.get_order_by_number(order_number), message="Order fetched")


@router.get("/{order_id}", response_model=ApiResponse[OrderDetail], dependencies=[ORD_VIEW],
            summary="Order with line items, customer, handler, totals and allowed next statuses")
def get_order(order_id: int, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.get_order(order_id), message="Order fetched")


@router.post("", response_model=ApiResponse[OrderDetail], status_code=201,
             summary="Create an empty pending order (add items next)")
def create_order(
    body: OrderCreate,
    actor: EmployeeResponse = Depends(ORD_EDIT_GUARD),
    service: OrderService = Depends(get_order_service),
):
    return ApiResponse(data=service.create_order(body, actor), message="Order created")


@router.put("/{order_id}", response_model=ApiResponse[OrderDetail], dependencies=[ORD_EDIT],
            summary="Change customer, handler, date or notes (pending orders only)")
def update_order(order_id: int, body: OrderUpdate, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.update_order(order_id, body), message="Order updated")


@router.patch("/{order_id}/status", response_model=ApiResponse[OrderDetail], dependencies=[ORD_EDIT],
              summary="Move an order to its next status, or cancel it")
def change_order_status(order_id: int, body: OrderStatusUpdate,
                        service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.change_status(order_id, body.status), message="Status updated")


@router.delete("/{order_id}", response_model=ApiResponse[None], dependencies=[ORD_FULL],
               summary="Soft-delete a pending or cancelled order")
def delete_order(order_id: int, service: OrderService = Depends(get_order_service)):
    service.delete_order(order_id)
    return ApiResponse(data=None, message="Order deleted")


@router.post("/{order_id}/restore", response_model=ApiResponse[OrderDetail], dependencies=[ORD_FULL])
def restore_order(order_id: int, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.restore_order(order_id), message="Order restored")


@router.post("/{order_id}/items", response_model=ApiResponse[OrderDetail], dependencies=[ORD_EDIT],
             summary="Add a product (uses its current price; same product again adds to the quantity)")
def add_order_item(order_id: int, body: OrderItemCreate, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.add_item(order_id, body), message="Item added")


@router.put("/{order_id}/items/{item_id}", response_model=ApiResponse[OrderDetail], dependencies=[ORD_EDIT],
            summary="Change a line's quantity")
def update_order_item(order_id: int, item_id: int, body: OrderItemUpdate,
                      service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.update_item(order_id, item_id, body), message="Item updated")


@router.delete("/{order_id}/items/{item_id}", response_model=ApiResponse[OrderDetail], dependencies=[ORD_EDIT],
               summary="Remove a line")
def remove_order_item(order_id: int, item_id: int, service: OrderService = Depends(get_order_service)):
    return ApiResponse(data=service.remove_item(order_id, item_id), message="Item removed")
