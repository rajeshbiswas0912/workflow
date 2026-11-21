from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.enums.order import OrderStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.employee import EmployeeResponse
from app.schemas.order import GST_RATE, OrderActivity, OrderCreate, OrderCustomer, OrderDetail, OrderEmployee, OrderItemUpdate, OrderLine, OrderListItem, OrderPage, OrderUpdate
from app.schemas.order_item import OrderItemCreate
from app.utils.db_errors import db_errors
from app.utils.exceptions import BadRequestError, ConflictError, NotFoundError
from app.utils.order_rules import ALLOWED_TRANSITIONS, DELETABLE_STATUSES, EDITABLE_STATUSES


class OrderService:
    def __init__(self, db: Session, orders: OrderRepository, products: ProductRepository):
        self._db = db
        self._orders = orders
        self._products = products

    # ---------- reads ----------
    def list_orders(self, search: str | None, customer_id: int | None, handled_by_id: int | None,
                    status: OrderStatus | None, date_from: date | None, date_to: date | None,
                    include_deleted: bool, limit: int, offset: int) -> OrderPage:
        with db_errors(self._db):
            rows = self._orders.list_all(search, customer_id, handled_by_id,
                                         status.value if status else None,
                                         date_from, date_to, include_deleted, limit, offset)
            counts = self._orders.status_counts(search, customer_id, handled_by_id, date_from, date_to)
        status_counts = {str(c["status"]): c["order_count"] for c in counts}
        status_counts["all"] = sum(status_counts.values())
        return OrderPage(
            items=[OrderListItem(**r) for r in rows],
            total=rows[0]["total_count"] if rows else 0,
            limit=limit,
            offset=offset,
            status_counts=status_counts,
        )

    def get_order(self, order_id: int) -> OrderDetail:
        with db_errors(self._db):
            row = self._get_row(order_id)
            items = self._orders.list_items(order_id)
        return self._build_detail(row, items)

    def get_order_by_number(self, order_number: str) -> OrderDetail:
        with db_errors(self._db):
            row = self._orders.get_by_number(order_number)
        if row is None:
            raise NotFoundError("No order with that number")
        return self.get_order(row["id"])

    # ---------- orders: writes ----------
    def create_order(self, data: OrderCreate, actor: EmployeeResponse) -> OrderDetail:
        with db_errors(self._db):
            new_id = self._orders.create(
                self._orders.next_number(), data.customer_id, data.handled_by_id or actor.id,
                data.order_date or date.today(), Decimal("0.00"), OrderStatus.PENDING.value, data.notes,
            )
            self._db.commit()
        return self.get_order(new_id)

    def update_order(self, order_id: int, data: OrderUpdate) -> OrderDetail:
        with db_errors(self._db):
            current = self._get_row(order_id)
            self._assert_editable(current)

            sent = data.model_fields_set
            merged = {f: getattr(data, f) if f in sent else current[f]
                      for f in ("customer_id", "handled_by_id", "order_date", "notes")}
            self._orders.update(order_id, current["order_number"], merged["customer_id"],
                                merged["handled_by_id"], merged["order_date"],
                                current["total_amount"], merged["notes"])
            self._db.commit()
        return self.get_order(order_id)

    def change_status(self, order_id: int, new_status: OrderStatus) -> OrderDetail:
        with db_errors(self._db):
            current = self._get_row(order_id)
            old_status = OrderStatus(current["status"])
            if new_status not in ALLOWED_TRANSITIONS[old_status]:
                raise ConflictError(f"An order can't move from {old_status.value} to {new_status.value}")
            if new_status == OrderStatus.CONFIRMED and current["item_count"] == 0:
                raise BadRequestError("Add at least one item before confirming the order")
            self._orders.change_status(order_id, new_status.value)
            self._db.commit()
        return self.get_order(order_id)

    def delete_order(self, order_id: int) -> None:
        with db_errors(self._db):
            current = self._get_row(order_id)
            if OrderStatus(current["status"]) not in DELETABLE_STATUSES:
                raise ConflictError("Only pending or cancelled orders can be deleted")
            self._orders.delete(order_id)
            self._db.commit()

    def restore_order(self, order_id: int) -> OrderDetail:
        with db_errors(self._db):
            self._orders.restore(order_id)
            self._db.commit()
        return self.get_order(order_id)

    # ---------- line items ----------
    def add_item(self, order_id: int, data: OrderItemCreate) -> OrderDetail:
        with db_errors(self._db):
            self._assert_editable(self._get_row(order_id))

            product = self._products.get_by_id(data.product_id)
            if product is None:
                raise NotFoundError(f"Product with ID {data.product_id} not found")
            if not product["is_active"]:
                raise BadRequestError("This product is discontinued and can't be added to an order")

            existing = next((i for i in self._orders.list_items(order_id)
                             if i["product_id"] == data.product_id), None)
            if existing:
                self._orders.update_item(existing["id"], data.product_id,
                                         existing["quantity"] + data.quantity, existing["unit_price"])
            else:
                self._orders.create_item(order_id, data.product_id, data.quantity, product["unit_price"])
            self._db.commit()
        return self.get_order(order_id)

    def update_item(self, order_id: int, item_id: int, data: OrderItemUpdate) -> OrderDetail:
        with db_errors(self._db):
            self._assert_editable(self._get_row(order_id))
            item = self._get_item(order_id, item_id)
            self._orders.update_item(item_id, item["product_id"], data.quantity, item["unit_price"])
            self._db.commit()
        return self.get_order(order_id)

    def remove_item(self, order_id: int, item_id: int) -> OrderDetail:
        with db_errors(self._db):
            self._assert_editable(self._get_row(order_id))
            self._get_item(order_id, item_id)
            self._orders.delete_item(item_id)
            self._db.commit()
        return self.get_order(order_id)

    # ---------- helpers ----------
    def _get_row(self, order_id: int) -> dict:
        row = self._orders.get_by_id(order_id)
        if row is None:
            raise NotFoundError(f"Order with ID {order_id} not found")
        return row

    def _get_item(self, order_id: int, item_id: int) -> dict:
        item = self._orders.get_item(item_id)
        if item is None or item["order_id"] != order_id:
            raise NotFoundError(f"Item {item_id} not found in order {order_id}")
        return item

    @staticmethod
    def _assert_editable(row: dict) -> None:
        if OrderStatus(row["status"]) not in EDITABLE_STATUSES:
            raise ConflictError("Only pending orders can be changed")

    @staticmethod
    def _build_detail(row: dict, items: list[dict]) -> OrderDetail:
        lines = [OrderLine(**i) for i in items]
        subtotal = sum((line.subtotal for line in lines), Decimal("0.00"))
        status = OrderStatus(row["status"])
        total = row["total_amount"]
        return OrderDetail(
            id=row["id"],
            order_number=row["order_number"],
            status=status,
            order_date=row["order_date"],
            notes=row["notes"],
            customer=OrderCustomer(id=row["customer_id"], name=row["customer_name"],
                                   email=row["customer_email"], city=row["customer_city"]),
            handled_by=OrderEmployee(id=row["handled_by_id"], name=row["handled_by_name"],
                                     job_title=row["handled_by_job_title"]),
            items=lines,
            item_count=len(lines),
            subtotal=subtotal,
            gst_rate_percent=GST_RATE * 100,
            gst_amount=total - subtotal,
            total_amount=total,
            allowed_next_statuses=ALLOWED_TRANSITIONS[status],
            activity=[OrderActivity(event="Order placed", by=row["handled_by_name"], at=row["created_at"])],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )
