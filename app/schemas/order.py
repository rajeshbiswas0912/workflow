from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from app.enums.order import OrderStatus
from app.schemas.order_item import OrderItemCreate, OrderItemResponse


class OrderCustomerSummary(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderEmployeeSummary(BaseModel):
    id: int
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    handled_by_id: int = Field(gt=0)
    order_date: date
    status: OrderStatus = OrderStatus.PENDING
    notes: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class OrderUpdate(BaseModel):
    customer_id: int | None = Field(default=None, gt=0)
    handled_by_id: int | None = Field(default=None, gt=0)
    order_date: date | None = None
    status: OrderStatus | None = None
    notes: str | None = None
    items: list[OrderItemCreate] | None = Field(default=None, min_length=1)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    handled_by_id: int
    order_date: date
    total_amount: Decimal
    status: OrderStatus
    notes: str | None
    customer: OrderCustomerSummary | None = None
    handled_by: OrderEmployeeSummary | None = None
    items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @computed_field
    @property
    def status_label(self) -> str:
        return self.status.label

    @computed_field
    @property
    def line_items_count(self) -> int:
        return len(self.items)

    model_config = ConfigDict(from_attributes=True)


# --- Top Filter Tabs Count Schema ---
class OrderStatusCounts(BaseModel):
    all: int = 0
    pending: int = 0
    confirmed: int = 0
    shipped: int = 0
    delivered: int = 0
    cancelled: int = 0
