from fastapi import APIRouter, Depends, Query

from app.enums.employee import EmployeeStatus
from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse, ErrorResponse
from app.schemas.employee import EmployeeCreate, EmployeeList, EmployeeResponse, EmployeeStatusUpdate, EmployeeUpdate
from app.services.employee_service import EmployeeService
from app.services.permission_service import PermissionService
from app.utils.dependencies import CurrentUser, get_employee_service, get_permission_service, require_permission


router = APIRouter(prefix="/employees", tags=["Employees"])

_VALIDATION = {422: {"model": ErrorResponse}}
_AUTH = {401: {"model": ErrorResponse}, **_VALIDATION}
_OWNER = {403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, **_AUTH}

EMP_VIEW = require_permission(PermissionArea.employees, PermissionLevel.view)
EMP_EDIT = require_permission(PermissionArea.employees, PermissionLevel.edit)
EMP_FULL = require_permission(PermissionArea.employees, PermissionLevel.full)

@router.get(
    "/profile",
    response_model=ApiResponse[EmployeeResponse],
    summary="Get the logged-in user's profile",
    responses={401: {"model": ErrorResponse}},
)
def get_profile(current_user: CurrentUser) -> ApiResponse[EmployeeResponse]:
    return ApiResponse(
        data=EmployeeResponse.model_validate(current_user),
        message="Profile fetched",
    )

@router.get(
    "/profile/permissions",
    response_model=ApiResponse[dict[PermissionArea, PermissionLevel]]
)
def my_permissions(current_user: CurrentUser, service: PermissionService = Depends(get_permission_service)):
    return ApiResponse(data=service.effective_permissions(current_user.role_id), message="Permissions fetched")


@router.get("", response_model=ApiResponse[EmployeeList], dependencies=[Depends(EMP_VIEW)],
            summary="List employees (search, department, role, status filters)")
def list_employees(
    search: str | None = None,
    department_id: int | None = None,
    role_id: int | None = None,
    status: EmployeeStatus | None = None,
    include_deleted: bool = False,
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: EmployeeService = Depends(get_employee_service),
):
    return ApiResponse(
        data=service.list_employees(search, department_id, role_id, status, include_deleted, limit, offset),
        message="Employees fetched",
    )


@router.get("/{employee_id}", response_model=ApiResponse[EmployeeResponse], dependencies=[Depends(EMP_VIEW)])
def get_employee(employee_id: int, service: EmployeeService = Depends(get_employee_service)):
    return ApiResponse(data=service.get_employee(employee_id), message="Employee fetched")


@router.post("", response_model=ApiResponse[EmployeeResponse], status_code=201)
def create_employee(
    body: EmployeeCreate,
    actor: EmployeeResponse = Depends(EMP_EDIT),
    service: EmployeeService = Depends(get_employee_service),
):
    return ApiResponse(data=service.create_employee(body, actor), message="Employee created")


@router.put("/{employee_id}", response_model=ApiResponse[EmployeeResponse],
            summary="Update an employee (omitted fields are kept)")
def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    actor: EmployeeResponse = Depends(EMP_EDIT),
    service: EmployeeService = Depends(get_employee_service),
):
    return ApiResponse(data=service.update_employee(employee_id, body, actor), message="Employee updated")


@router.patch("/{employee_id}/status", response_model=ApiResponse[EmployeeResponse])
def change_employee_status(
    employee_id: int,
    body: EmployeeStatusUpdate,
    actor: EmployeeResponse = Depends(EMP_EDIT),
    service: EmployeeService = Depends(get_employee_service),
):
    return ApiResponse(data=service.change_status(employee_id, body.status, actor), message="Status updated")


@router.delete("/{employee_id}", response_model=ApiResponse[None],
               summary="Soft-delete an employee (blocked while they have active subordinates)")
def delete_employee(
    employee_id: int,
    actor: EmployeeResponse = Depends(EMP_FULL),
    service: EmployeeService = Depends(get_employee_service),
):
    service.delete_employee(employee_id, actor)
    return ApiResponse(data=None, message="Employee deleted")


@router.post("/{employee_id}/restore", response_model=ApiResponse[EmployeeResponse])
def restore_employee(
    employee_id: int,
    actor: EmployeeResponse = Depends(EMP_FULL),
    service: EmployeeService = Depends(get_employee_service),
):
    return ApiResponse(data=service.restore_employee(employee_id, actor), message="Employee restored")
