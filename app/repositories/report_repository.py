from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session


class ReportRepository:
    def __init__(self, db: Session):
        self._db = db

    def _fail_fast(self) -> None:
        self._db.execute(text("SET LOCAL statement_timeout = 5000"))

    def sales_by_month(self, end_month: date, months: int) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(
            text("SELECT * FROM fn_dashboard_sales_by_month(CAST(:m AS DATE), CAST(:n AS INT))"),
            {"m": end_month, "n": months},
        ).mappings().all()
        return [dict(r) for r in rows]

    def top_customers(self, date_from: date, date_to: date, limit: int) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(
            text("SELECT * FROM fn_report_top_customers(CAST(:f AS DATE), CAST(:t AS DATE), CAST(:l AS INT))"),
            {"f": date_from, "t": date_to, "l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def orders_per_employee(self, date_from: date, date_to: date, limit: int) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(
            text("SELECT * FROM fn_report_orders_per_employee(CAST(:f AS DATE), CAST(:t AS DATE), CAST(:l AS INT))"),
            {"f": date_from, "t": date_to, "l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def department_summary(self) -> list[dict]:
        self._fail_fast()
        rows = self._db.execute(text("SELECT * FROM fn_report_department_summary()")).mappings().all()
        return [dict(r) for r in rows]
