# app/services/dashboard_service.py
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.enums.order import OrderStatus
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard_schema import CustomerStat, EmployeeStat, MonthlySales, OpenOrdersStat, OrdersByStatus, RevenueStat, StatusCount
from app.schemas.order import OrderListItem
from app.utils.db_errors import db_errors
from app.utils.order_rules import OPEN_STATUSES

APP_TZ = ZoneInfo("Asia/Kolkata")


def _this_month() -> date:
    return datetime.now(APP_TZ).date().replace(day=1)


class DashboardService:
    def __init__(self, db: Session, repo: DashboardRepository):
        self._db = db
        self._repo = repo

    def employees(self) -> EmployeeStat:
        with db_errors(self._db):
            row = self._repo.employees()
        return EmployeeStat(total=row["employee_count"], departments=row["department_count"])

    def customers(self) -> CustomerStat:
        with db_errors(self._db):
            total = self._repo.customers()
        return CustomerStat(total=total)

    def revenue(self) -> RevenueStat:
        month = _this_month()
        with db_errors(self._db):
            row = self._repo.revenue(month)
        return RevenueStat(month=month.strftime("%Y-%m"), month_label=month.strftime("%B %Y"),
                           amount=row["revenue"], order_count=row["order_count"])

    def sales_by_month(self, months: int) -> list[MonthlySales]:
        current = _this_month()
        with db_errors(self._db):
            rows = self._repo.sales_by_month(current, months)
        return [
            MonthlySales(month=r["month_start"].strftime("%Y-%m"), label=r["month_start"].strftime("%b"),
                         total_sales=r["total_sales"], order_count=r["order_count"],
                         is_current=r["month_start"] == current)
            for r in rows
        ]

    def open_orders(self) -> OpenOrdersStat:
        counts = self._status_counts()
        return OpenOrdersStat(open=sum(counts.get(s, 0) for s in OPEN_STATUSES),
                              pending=counts.get(OrderStatus.PENDING, 0))

    def orders_by_status(self) -> OrdersByStatus:
        counts = self._status_counts()
        return OrdersByStatus(
            total=sum(counts.values()),
            statuses=[StatusCount(status=s, label=s.value.replace("_", " ").capitalize(), count=counts.get(s, 0))
                      for s in OrderStatus],
        )

    def recent_orders(self, limit: int) -> list[OrderListItem]:
        with db_errors(self._db):
            rows = self._repo.recent_orders(limit)
        return [OrderListItem(**r) for r in rows]

    def _status_counts(self) -> dict[OrderStatus, int]:
        with db_errors(self._db):
            rows = self._repo.status_counts()
        return {OrderStatus(r["status"]): r["order_count"] for r in rows}
