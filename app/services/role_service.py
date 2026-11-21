from sqlalchemy.orm import Session

from app.enums.permission import PermissionArea, PermissionLevel
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.employee import RoleSummary
from app.schemas.role import RoleCreate, RoleDetail, RoleListItem, RoleRead, RoleUpdate
from app.schemas.role_permission import RolePermissionItem
from app.utils.db_errors import db_errors
from app.utils.exceptions import ForbiddenError, NotFoundError

def _to_json(items: list[RolePermissionItem]) -> dict[str, str]:
    return {i.area.value: i.access_level.value for i in items}

class RoleService:
    def __init__(self, db: Session, roles: RoleRepository, perms: PermissionRepository):
        self._db = db
        self._roles = roles
        self._perms = perms

    def _get_summary(self, role_id: int) -> dict:
        rows = self._perms.summaries(role_id=role_id)
        if not rows:
            raise NotFoundError(f"Role with ID {role_id} not found")
        return rows[0]

    def _get_editable(self, role_id: int) -> dict:
        summary = self._get_summary(role_id)
        if summary["is_system"]:
            raise ForbiddenError("The Admin role can't be changed")
        return summary

    def list_roles(self, is_active: bool | None = None) -> list[RoleListItem]:
        with db_errors(self._db):
            rows = self._perms.summaries(is_active=is_active)
        return [RoleListItem(**r) for r in rows]

    def get_role(self, role_id: int) -> RoleDetail:
        with db_errors(self._db):
            summary = self._get_summary(role_id)
            grid = self._perms.get_grid(role_id)
        return RoleDetail(
            **summary,
            permissions=[RolePermissionItem(**g) for g in grid],
        )

    def create_role(self, data: RoleCreate) -> RoleDetail:
        with db_errors(self._db):
            role = self._roles.create(data.name, data.is_active)
            if data.permissions:
                self._perms.set_grid(role["id"], _to_json(data.permissions))
            self._db.commit()
        return self.get_role(role["id"])

    def update_role(self, role_id: int, data: RoleUpdate) -> RoleDetail:
        with db_errors(self._db):
            self._get_editable(role_id)
            if data.name is not None or data.is_active is not None:
                self._roles.update(role_id, data.name, data.is_active)
            if data.permissions is not None:
                self._perms.set_grid(role_id, _to_json(data.permissions))
            self._db.commit()
        return self.get_role(role_id)

    def get_permissions(self, role_id: int) -> list[RolePermissionItem]:
        with db_errors(self._db):
            self._get_summary(role_id)
            grid = self._perms.get_grid(role_id)
        return [RolePermissionItem(**g) for g in grid]

    def replace_permissions(self, role_id: int, items: list[RolePermissionItem]) -> list[RolePermissionItem]:
        with db_errors(self._db):
            self._get_editable(role_id)
            self._perms.set_grid(role_id, _to_json(items))
            self._db.commit()
        return self.get_permissions(role_id)

    def set_permission(
        self, role_id: int, area: PermissionArea, level: PermissionLevel
    ) -> list[RolePermissionItem]:
        with db_errors(self._db):
            self._get_editable(role_id)
            self._perms.set_one(role_id, area.value, level.value)
            self._db.commit()
        return self.get_permissions(role_id)

    def reset_permissions(self, role_id: int) -> list[RolePermissionItem]:
        with db_errors(self._db):
            self._get_editable(role_id)
            self._perms.reset(role_id)
            self._db.commit()
        return self.get_permissions(role_id)
