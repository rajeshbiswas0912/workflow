from fastapi import APIRouter, Depends

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import ApiResponse
from app.schemas.role import PermissionLevelUpdate, RoleCreate, RoleDetail, RoleListItem, RolePermissionsReplace, RoleRead, RoleUpdate
from app.schemas.role_permission import RolePermissionItem
from app.services.role_service import RoleService
from app.utils.dependencies import get_role_service, require_permission


router = APIRouter(prefix="/roles", tags=["Roles"])

SETTINGS_VIEW = Depends(require_permission(PermissionArea.settings, PermissionLevel.view))
SETTINGS_FULL = Depends(require_permission(PermissionArea.settings, PermissionLevel.full))


@router.get(
    "",
    response_model=ApiResponse[list[RoleListItem]],
    dependencies=[SETTINGS_VIEW],
    summary="List roles with people count and area access"
)
def list_roles(is_active: bool | None = None, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.list_roles(is_active), message="Roles fetched")


@router.get(
    "/{role_id}",
    response_model=ApiResponse[RoleDetail],
    dependencies=[SETTINGS_VIEW],
    summary="Get one role with its permission grid"
)
def get_role(role_id: int, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.get_role(role_id), message="Role fetched")


@router.post(
    "",
    response_model=ApiResponse[RoleDetail],
    status_code=201,
    dependencies=[SETTINGS_FULL],
    summary="Create a role with its permissions"
)
def create_role(body: RoleCreate, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.create_role(body), message="Role created")


@router.put(
    "/{role_id}",
    response_model=ApiResponse[RoleDetail],
    dependencies=[SETTINGS_FULL],
    summary="Update a role's name, status and/or permissions"
)
def update_role(role_id: int, body: RoleUpdate, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.update_role(role_id, body), message="Role updated")


@router.get(
    "/{role_id}/permissions",
    response_model=ApiResponse[list[RolePermissionItem]],
    dependencies=[SETTINGS_VIEW],
    summary="Get a role's permission grid"
)
def get_permissions(role_id: int, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.get_permissions(role_id), message="Permissions fetched")


@router.put(
    "/{role_id}/permissions",
    response_model=ApiResponse[list[RolePermissionItem]],
    dependencies=[SETTINGS_FULL],
    summary="Replace a role's whole permission grid"
)
def replace_permissions(role_id: int, body: RolePermissionsReplace, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.replace_permissions(role_id, body.permissions), message="Permissions updated")


@router.patch(
    "/{role_id}/permissions/{area}",
    response_model=ApiResponse[list[RolePermissionItem]],
    dependencies=[SETTINGS_FULL],
    summary="Change one area's access level"
)
def set_permission(role_id: int, area: PermissionArea, body: PermissionLevelUpdate, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.set_permission(role_id, area, body.access_level), message="Permission updated")


@router.delete(
    "/{role_id}/permissions",
    response_model=ApiResponse[list[RolePermissionItem]],
    dependencies=[SETTINGS_FULL],
    summary="Reset a role to no access"
)
def reset_permissions(role_id: int, service: RoleService = Depends(get_role_service)):
    return ApiResponse(data=service.reset_permissions(role_id), message="Permissions reset")
