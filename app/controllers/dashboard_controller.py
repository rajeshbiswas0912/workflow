from fastapi import APIRouter, Depends, Query

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.dashboard_schema import CustomerStat, EmployeeStat, MonthlySales, OpenOrdersStat, OrdersByStatus, RevenueStat
from app.schemas.order import OrderListItem
from app.services.dashboard_service import DashboardService
from app.utils.dependencies import get_dashboard_service, require_permission


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

EMP_VIEW = Depends(require_permission(PermissionArea.employees, PermissionLevel.view))
CUST_VIEW = Depends(require_permission(PermissionArea.customers, PermissionLevel.view))
ORD_VIEW = Depends(require_permission(PermissionArea.orders, PermissionLevel.view))


@router.get("/employees", response_model=ApiResponse[EmployeeStat], dependencies=[EMP_VIEW])
def employee_stat(service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.employees(), message="Employee stats fetched")


@router.get("/open-orders", response_model=ApiResponse[OpenOrdersStat], dependencies=[ORD_VIEW])
def open_orders(service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.open_orders(), message="Open orders fetched")


@router.get("/revenue", response_model=ApiResponse[RevenueStat], dependencies=[ORD_VIEW],
            summary="Revenue for the current month (cancelled orders excluded)")
def revenue(service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.revenue(), message="Revenue fetched")


@router.get("/customers", response_model=ApiResponse[CustomerStat], dependencies=[CUST_VIEW])
def customer_stat(service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.customers(), message="Customer stats fetched")


@router.get("/sales-by-month", response_model=ApiResponse[list[MonthlySales]], dependencies=[ORD_VIEW])
def sales_by_month(months: int = Query(6, ge=1, le=24),
                   service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.sales_by_month(months), message="Sales by month fetched")


@router.get("/orders-by-status", response_model=ApiResponse[OrdersByStatus], dependencies=[ORD_VIEW])
def orders_by_status(service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.orders_by_status(), message="Orders by status fetched")


@router.get("/recent-orders", response_model=ApiResponse[list[OrderListItem]], dependencies=[ORD_VIEW])
def recent_orders(limit: int = Query(5, ge=1, le=20),
                  service: DashboardService = Depends(get_dashboard_service)):
    return ApiResponse(data=service.recent_orders(limit), message="Recent orders fetched")
