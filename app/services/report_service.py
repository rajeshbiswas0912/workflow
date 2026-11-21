import csv
import io
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository
from app.schemas.dashboard_schema import MonthlySales
from app.schemas.report_schema import DepartmentRow, DepartmentSummary, EmployeeOrders, OrdersPerEmployeeReport, SalesByMonthReport, TopCustomer, TopCustomersReport
from app.utils.db_errors import db_errors
from app.utils.report_period import DateRange, ReportPeriod, resolve_period


def _safe(value):
    """Stop spreadsheet formula injection from user-entered names."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


class ReportService:
    def __init__(self, db: Session, repo: ReportRepository):
        self._db = db
        self._repo = repo

    @staticmethod
    def _info(period: ReportPeriod) -> tuple[dict, "DateRange"]:
        rng = resolve_period(period)
        return {"period": period, "label": period.label, "date_from": rng.start, "date_to": rng.end}, rng

    def sales_by_month(self, period: ReportPeriod) -> SalesByMonthReport:
        info, rng = self._info(period)
        current = rng.end.replace(day=1)
        with db_errors(self._db):
            rows = self._repo.sales_by_month(rng.end, rng.months)
        months = [
            MonthlySales(month=r["month_start"].strftime("%Y-%m"), label=r["month_start"].strftime("%b"),
                         total_sales=r["total_sales"], order_count=r["order_count"],
                         is_current=r["month_start"] == current)
            for r in rows
        ]
        return SalesByMonthReport(**info, months=months,
                                  total=sum((m.total_sales for m in months), Decimal("0.00")))

    def top_customers(self, period: ReportPeriod, limit: int) -> TopCustomersReport:
        info, rng = self._info(period)
        with db_errors(self._db):
            rows = self._repo.top_customers(rng.start, rng.end, limit)
        return TopCustomersReport(**info, items=[
            TopCustomer(customer_id=r["customer_id"], name=r["customer_name"],
                        total_spent=r["total_spent"], order_count=r["order_count"]) for r in rows
        ])

    def orders_per_employee(self, period: ReportPeriod, limit: int) -> OrdersPerEmployeeReport:
        info, rng = self._info(period)
        with db_errors(self._db):
            rows = self._repo.orders_per_employee(rng.start, rng.end, limit)
        return OrdersPerEmployeeReport(**info, items=[
            EmployeeOrders(employee_id=r["employee_id"], name=r["employee_name"],
                           order_count=r["order_count"], total_sales=r["total_sales"]) for r in rows
        ])

    def department_summary(self) -> DepartmentSummary:
        with db_errors(self._db):
            rows = self._repo.department_summary()
        items = [
            DepartmentRow(department_id=r["department_id"], name=r["department_name"],
                          employee_count=r["employee_count"], average_salary=r["average_salary"],
                          monthly_payroll=r["monthly_payroll"]) for r in rows
        ]
        return DepartmentSummary(
            rows=items,
            total_employees=sum(i.employee_count for i in items),
            total_payroll=sum((i.monthly_payroll for i in items), Decimal("0")),
        )

    def export_csv(self, period: ReportPeriod, limit: int = 50) -> tuple[str, bytes]:
        sales = self.sales_by_month(period)
        customers = self.top_customers(period, limit)
        employees = self.orders_per_employee(period, limit)
        departments = self.department_summary()

        out = io.StringIO()
        w = csv.writer(out)

        w.writerow(["Report", f"{sales.label} ({sales.date_from} to {sales.date_to})"])
        w.writerow([])
        w.writerow(["Sales by month"])
        w.writerow(["Month", "Total sales (INR)", "Orders"])
        for m in sales.months:
            w.writerow([m.month, m.total_sales, m.order_count])
        w.writerow(["Total", sales.total, ""])
        w.writerow([])
        w.writerow(["Top customers by spend"])
        w.writerow(["Customer", "Total spent (INR)", "Orders"])
        for c in customers.items:
            w.writerow([_safe(c.name), c.total_spent, c.order_count])
        w.writerow([])
        w.writerow(["Orders handled per employee"])
        w.writerow(["Employee", "Orders", "Total sales (INR)"])
        for e in employees.items:
            w.writerow([_safe(e.name), e.order_count, e.total_sales])
        w.writerow([])
        w.writerow(["Headcount and salary by department (current)"])
        w.writerow(["Department", "Employees", "Average salary (INR)", "Monthly payroll (INR)"])
        for d in departments.rows:
            w.writerow([_safe(d.name), d.employee_count, d.average_salary, d.monthly_payroll])
        w.writerow(["Total", departments.total_employees, "", departments.total_payroll])

        filename = f"report-{period.value}-{sales.date_to}.csv"
        return filename, out.getvalue().encode("utf-8-sig")
