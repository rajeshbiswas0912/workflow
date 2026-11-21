# app/schemas/report_api.py
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.dashboard_schema import MonthlySales
from app.utils.report_period import ReportPeriod



class PeriodInfo(BaseModel):
    period: ReportPeriod
    label: str
    date_from: date
    date_to: date


class SalesByMonthReport(PeriodInfo):
    months: list[MonthlySales]
    total: Decimal


class TopCustomer(BaseModel):
    customer_id: int
    name: str
    total_spent: Decimal
    order_count: int


class TopCustomersReport(PeriodInfo):
    items: list[TopCustomer]


class EmployeeOrders(BaseModel):
    employee_id: int
    name: str
    order_count: int
    total_sales: Decimal


class OrdersPerEmployeeReport(PeriodInfo):
    items: list[EmployeeOrders]


class DepartmentRow(BaseModel):
    department_id: int
    name: str
    employee_count: int
    average_salary: Decimal
    monthly_payroll: Decimal


class DepartmentSummary(BaseModel):
    rows: list[DepartmentRow]
    total_employees: int
    total_payroll: Decimal
