from pydantic import BaseModel, ConfigDict

from app.enums.permission import PermissionArea, PermissionLevel


class RolePermissionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area: PermissionArea
    access_level: PermissionLevel
