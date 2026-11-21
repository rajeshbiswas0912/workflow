from decimal import Decimal

from pydantic import BaseModel

from app.enums.order import OrderStatus


class EmployeeStat(BaseModel):
    total: int
    departments: int


class OpenOrdersStat(BaseModel):
    open: int
    pending: int


class RevenueStat(BaseModel):
    month: str
    month_label: str
    amount: Decimal
    order_count: int


class CustomerStat(BaseModel):
    total: int


class MonthlySales(BaseModel):
    month: str
    label: str
    total_sales: Decimal
    order_count: int
    is_current: bool


class StatusCount(BaseModel):
    status: OrderStatus
    label: str
    count: int


class OrdersByStatus(BaseModel):
    total: int
    statuses: list[StatusCount]
