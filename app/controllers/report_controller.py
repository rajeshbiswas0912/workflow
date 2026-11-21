from fastapi import APIRouter, Depends, Query, Response

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.report_schema import DepartmentSummary, OrdersPerEmployeeReport, SalesByMonthReport, TopCustomersReport
from app.services.report_service import ReportService
from app.utils.dependencies import get_report_service, require_permission
from app.utils.report_period import ReportPeriod

router = APIRouter(prefix="/reports", tags=["Reports"])

REPORT_VIEW = Depends(require_permission(PermissionArea.reports, PermissionLevel.view))


@router.get("/sales-by-month", response_model=ApiResponse[SalesByMonthReport], dependencies=[REPORT_VIEW])
def sales_by_month(period: ReportPeriod = ReportPeriod.LAST_6_MONTHS,
                   service: ReportService = Depends(get_report_service)):
    return ApiResponse(data=service.sales_by_month(period), message="Sales by month fetched")


@router.get("/top-customers", response_model=ApiResponse[TopCustomersReport], dependencies=[REPORT_VIEW])
def top_customers(period: ReportPeriod = ReportPeriod.LAST_6_MONTHS,
                  limit: int = Query(5, ge=1, le=50),
                  service: ReportService = Depends(get_report_service)):
    return ApiResponse(data=service.top_customers(period, limit), message="Top customers fetched")


@router.get("/orders-per-employee", response_model=ApiResponse[OrdersPerEmployeeReport],
            dependencies=[REPORT_VIEW])
def orders_per_employee(period: ReportPeriod = ReportPeriod.LAST_6_MONTHS,
                        limit: int = Query(5, ge=1, le=50),
                        service: ReportService = Depends(get_report_service)):
    return ApiResponse(data=service.orders_per_employee(period, limit), message="Orders per employee fetched")


@router.get("/department-summary", response_model=ApiResponse[DepartmentSummary], dependencies=[REPORT_VIEW],
            summary="Headcount, average salary and payroll per department (current snapshot)")
def department_summary(service: ReportService = Depends(get_report_service)):
    return ApiResponse(data=service.department_summary(), message="Department summary fetched")


@router.get("/export", response_class=Response, dependencies=[REPORT_VIEW],
            summary="Download all four report sections as one CSV file")
def export_report(period: ReportPeriod = ReportPeriod.LAST_6_MONTHS,
                  service: ReportService = Depends(get_report_service)):
    filename, content = service.export_csv(period)
    return Response(content=content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
