# app/schemas/order_api.py
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.enums.order import OrderStatus
from app.schemas.common import UTCDateTime

GST_RATE = Decimal("0.18")


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: int
    handled_by_id: int | None = None
    order_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class OrderUpdate(BaseModel):
    """Omitted field = keep current value. null clears notes only."""
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: int | None = None
    handled_by_id: int | None = None
    order_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for f in ("customer_id", "handled_by_id", "order_date"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} can't be null")
        return self


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=1_000_000)


class OrderItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=1_000_000)


def _label(status: OrderStatus) -> str:
    return status.value.replace("_", " ").capitalize()


class OrderListItem(BaseModel):
    id: int
    order_number: str
    customer_id: int
    customer_name: str
    handled_by_id: int
    handled_by_name: str
    order_date: date
    total_amount: Decimal
    status: OrderStatus
    item_count: int
    created_at: UTCDateTime

    @computed_field
    @property
    def status_label(self) -> str:
        return _label(self.status)


class OrderPage(BaseModel):
    items: list[OrderListItem]
    total: int
    limit: int
    offset: int
    status_counts: dict[str, int]


class OrderLine(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_sku: str | None = None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderCustomer(BaseModel):
    id: int
    name: str
    email: str
    city: str | None = None


class OrderEmployee(BaseModel):
    id: int
    name: str
    job_title: str | None = None


class OrderActivity(BaseModel):
    event: str
    by: str
    at: UTCDateTime


class OrderDetail(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    order_date: date
    notes: str | None = None
    customer: OrderCustomer
    handled_by: OrderEmployee
    items: list[OrderLine]
    item_count: int
    subtotal: Decimal
    gst_rate_percent: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    allowed_next_statuses: list[OrderStatus]
    activity: list[OrderActivity]
    created_at: UTCDateTime
    updated_at: UTCDateTime
    deleted_at: UTCDateTime | None = None

    @computed_field
    @property
    def status_label(self) -> str:
        return _label(self.status)
