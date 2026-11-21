from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.settings import settings
from app.enums.permission import PermissionArea, PermissionLevel
from app.repositories.customer_repository import CustomerRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.employee import EmployeeResponse
from app.services.auth_service import AuthService
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from app.services.customer_service import CustomerService
from app.services.dashboard_service import DashboardService
from app.services.department_service import DepartmentService
from app.services.employee_service import EmployeeService
from app.services.order_service import OrderService
from app.services.permission_service import PermissionService
from app.services.product_service import ProductService
from app.services.report_service import ReportService
from app.services.role_service import RoleService
from app.utils.exceptions import ForbiddenError

bearer_scheme = HTTPBearer()

def get_employee_repository(db: Session = Depends(get_db)) -> EmployeeRepository:
    return EmployeeRepository(db)

def get_permission_repository(db: Session = Depends(get_db)) -> PermissionRepository:
    return PermissionRepository(db)

def get_role_repository(db: Session = Depends(get_db)) -> RoleRepository:
    return RoleRepository(db)

def get_department_repository(db: Session = Depends(get_db)) -> DepartmentRepository:
    return DepartmentRepository(db)

def get_customer_repository(db: Session = Depends(get_db)) -> CustomerRepository:
    return CustomerRepository(db)

def get_product_repository(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)

def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

def get_dashboard_repository(db: Session = Depends(get_db)) -> DashboardRepository:
    return DashboardRepository(db)

def get_report_repository(db: Session = Depends(get_db)) -> ReportRepository:
    return ReportRepository(db)

def get_auth_service(
    repo: EmployeeRepository = Depends(get_employee_repository),
) -> AuthService:
    return AuthService(repo)

def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> EmployeeResponse:
    return auth_service.get_current_user(creds.credentials)

def get_permission_service(
    perms: PermissionRepository = Depends(get_permission_repository),
) -> PermissionService:
    return PermissionService(perms)

def require_permission(area: PermissionArea, minimum: PermissionLevel):
    def checker(
        user: CurrentUser,
        service: PermissionService = Depends(get_permission_service),
    ) -> EmployeeResponse:
        if not service.has_permission(user.role_id, area, minimum):
            raise ForbiddenError("You don't have permission to do this")
        return user
    return checker

def get_role_service(
    db: Session = Depends(get_db),
    roles: RoleRepository = Depends(get_role_repository),
    perms: PermissionRepository = Depends(get_permission_repository),
) -> RoleService:
    return RoleService(db, roles, perms)

def get_department_service(
    db: Session = Depends(get_db),
    repo: DepartmentRepository = Depends(get_department_repository),
) -> DepartmentService:
    return DepartmentService(db, repo)

def get_employee_service(
    db: Session = Depends(get_db),
    repo: EmployeeRepository = Depends(get_employee_repository),
) -> EmployeeService:
    return EmployeeService(db, repo)

def get_customer_service(
    db: Session = Depends(get_db),
    repo: CustomerRepository = Depends(get_customer_repository),
) -> CustomerService:
    return CustomerService(db, repo)

def get_product_service(
    db: Session = Depends(get_db),
    repo: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    return ProductService(db, repo)

def get_order_service(
    db: Session = Depends(get_db),
    orders: OrderRepository = Depends(get_order_repository),
    products: ProductRepository = Depends(get_product_repository),
) -> OrderService:
    return OrderService(db, orders, products)

def get_dashboard_service(
    db: Session = Depends(get_db),
    repo: DashboardRepository = Depends(get_dashboard_repository),
) -> DashboardService:
    return DashboardService(db, repo)

def get_report_service(
    db: Session = Depends(get_db),
    repo: ReportRepository = Depends(get_report_repository),
) -> ReportService:
    return ReportService(db, repo)

CurrentUser = Annotated[EmployeeResponse, Depends(get_current_user)]
