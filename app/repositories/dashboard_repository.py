from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session


class DashboardRepository:
    def __init__(self, db: Session):
        self._db = db

    def _fail_fast(self) -> None:
        self._db.execute(text("SET LOCAL statement_timeout = 3000"))

    def employees(self) -> dict:
        self._fail_fast()
        return dict(self._db.execute(text("SELECT * FROM fn_dashboard_employees()")).mappings().one())

    def customers(self) -> int:
        self._fail_fast()
        return self._db.execute(text("SELECT customer_count FROM fn_dashboard_customers()")).scalar_one()

    def revenue(self, month_start: date) -> dict:
        self._fail_fast()
        return dict(self._db.execute(
            text("SELECT * FROM fn_dashboard_revenue(CAST(:m AS DATE))"), {"m": month_start},
        ).mappings().one())

    def sales_by_month(self, end_month: date, months: int) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(
            text("SELECT * FROM fn_dashboard_sales_by_month(CAST(:m AS DATE), CAST(:n AS INT))"),
            {"m": end_month, "n": months},
        ).mappings().all()
        return [dict(r) for r in rows]

    def status_counts(self) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(text("SELECT * FROM fn_order_status_counts()")).mappings().all()
        return [dict(r) for r in rows]

    def recent_orders(self, limit: int) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(
            text("SELECT * FROM fn_order_list(p_limit => CAST(:limit AS INT))"), {"limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]
