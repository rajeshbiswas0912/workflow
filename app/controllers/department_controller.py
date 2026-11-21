from fastapi import APIRouter, Depends, Query

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.department import DepartmentCreate, DepartmentHeadUpdate, DepartmentItem, DepartmentList, DepartmentUpdate
from app.services.department_service import DepartmentService
from app.utils.dependencies import get_department_service, require_permission

router = APIRouter(prefix="/departments", tags=["Departments"])

DEPT_VIEW = Depends(require_permission(PermissionArea.departments, PermissionLevel.view))
DEPT_EDIT = Depends(require_permission(PermissionArea.departments, PermissionLevel.edit))
DEPT_FULL = Depends(require_permission(PermissionArea.departments, PermissionLevel.full))


@router.get(
    "",
    response_model=ApiResponse[DepartmentList],
    dependencies=[DEPT_VIEW],
    summary="List departments with head name and employee count"
)
def list_departments(
    search: str | None = None,
    include_deleted: bool = False,
    limit: int = Query(10, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: DepartmentService = Depends(get_department_service),
):
    return ApiResponse(data=service.list_departments(search, include_deleted, limit, offset), message="Departments fetched")


@router.get(
    "/{department_id}",
    response_model=ApiResponse[DepartmentItem],
    dependencies=[DEPT_VIEW]
)
def get_department(department_id: int, service: DepartmentService = Depends(get_department_service)):
    return ApiResponse(data=service.get_department(department_id), message="Department fetched")


@router.post(
    "",
    response_model=ApiResponse[DepartmentItem],
    status_code=201,
    dependencies=[DEPT_EDIT]
)
def create_department(body: DepartmentCreate, service: DepartmentService = Depends(get_department_service)):
    return ApiResponse(data=service.create_department(body), message="Department created")


@router.put(
    "/{department_id}",
    response_model=ApiResponse[DepartmentItem],
    dependencies=[DEPT_EDIT],
    summary="Update name, description and/or head (omitted fields are kept)"
)
def update_department(
    department_id: int,
    body: DepartmentUpdate,
    service: DepartmentService = Depends(get_department_service)
):
    return ApiResponse(data=service.update_department(department_id, body), message="Department updated")


@router.put(
    "/{department_id}/head",
    response_model=ApiResponse[DepartmentItem],
    dependencies=[DEPT_EDIT],
    summary="Set or remove the department head"
)
def set_department_head(
    department_id: int,
    body: DepartmentHeadUpdate,
    service: DepartmentService = Depends(get_department_service)
):
    return ApiResponse(data=service.set_head(department_id, body.employee_id), message="Department head updated")


@router.delete(
    "/{department_id}",
    response_model=ApiResponse[None],
    dependencies=[DEPT_FULL],
    summary="Soft-delete a department (blocked while it has employees)"
)
def delete_department(department_id: int, service: DepartmentService = Depends(get_department_service)):
    service.delete_department(department_id)
    return ApiResponse(data=None, message="Department deleted")


@router.post(
    "/{department_id}/restore",
    response_model=ApiResponse[DepartmentItem],
    dependencies=[DEPT_FULL]
)
def restore_department(department_id: int, service: DepartmentService = Depends(get_department_service)):
    return ApiResponse(data=service.restore_department(department_id), message="Department restored")
