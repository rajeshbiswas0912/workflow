from app.enums.permission import PermissionArea, PermissionLevel
from app.repositories.permission_repository import PermissionRepository


class PermissionService:
    def __init__(self, permission_repository: PermissionRepository):
        self._perms = permission_repository

    def has_permission(self, role_id: int, area: PermissionArea, minimum: PermissionLevel) -> bool:
        return self._perms.has_permission(role_id, area.value, minimum.value)

    def effective_permissions(self, role_id: int) -> dict[PermissionArea, PermissionLevel]:
        rows = self._perms.summaries(role_id=role_id)
        if not rows or not rows[0]["is_active"]:
            return {a: PermissionLevel.none for a in PermissionArea}
        if rows[0]["is_system"]:
            return {a: PermissionLevel.full for a in PermissionArea}
        return {
            PermissionArea(g["area"]): PermissionLevel(g["access_level"])
            for g in self._perms.get_grid(role_id)
        }
