from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.enums.permission import PermissionArea, PermissionLevel
from app.schemas.common import UTCDateTime
from app.schemas.role_permission import RolePermissionItem

def _unique_areas(items: list[RolePermissionItem] | None):
    if items is not None:
        areas = [i.area for i in items]
        if len(areas) != len(set(areas)):
            raise ValueError("Each area can appear only once")
    return items

class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    permissions: list[RolePermissionItem] = []

    @field_validator("permissions")
    @classmethod
    def _unique_permission_areas(cls, value):
        return _unique_areas(value)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    permissions: list[RolePermissionItem] = []

    @field_validator("permissions")
    @classmethod
    def _unique_permission_areas(cls, value):
        return _unique_areas(value)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

class RolePermissionsReplace(BaseModel):
    permissions: list[RolePermissionItem]

    @field_validator("permissions")
    @classmethod
    def _unique_permission_areas(cls, value):
        return _unique_areas(value)

class PermissionLevelUpdate(BaseModel):
    access_level: PermissionLevel

class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime

class RoleListItem(BaseModel):
    id: int
    name: str
    is_active: bool
    is_system: bool
    people_count: int
    areas_with_access: int
    total_areas: int

class RoleDetail(RoleListItem):
    total_areas: int = len(PermissionArea)
    permissions: list[RolePermissionItem]
