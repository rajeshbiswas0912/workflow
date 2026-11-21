from app.enums.order import OrderStatus


ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING:   [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED:   [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}
EDITABLE_STATUSES = {OrderStatus.PENDING}
DELETABLE_STATUSES = {OrderStatus.PENDING, OrderStatus.CANCELLED}
OPEN_STATUSES = {OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.SHIPPED}
