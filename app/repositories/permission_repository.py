import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.helpers import clean_out_row


class PermissionRepository:
    def __init__(self, db: Session):
        self._db = db

    def summaries(self, role_id: int | None = None, is_active: bool | None = None) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM sp_get_role_permission_summary(
                        CAST(:role_id AS INTEGER), CAST(:is_active AS BOOLEAN))"""),
            {"role_id": role_id, "is_active": is_active},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_grid(self, role_id: int) -> list[dict]:
        rows = self._db.execute(
            text("SELECT area, access_level FROM sp_get_role_permissions(CAST(:role_id AS INTEGER))"),
            {"role_id": role_id},
        ).mappings().all()
        return [dict(r) for r in rows]

    def set_grid(self, role_id: int, permissions: dict[str, str]) -> int:
        row = self._db.execute(
            text("""CALL sp_set_role_permissions(CAST(:role_id AS INTEGER),
                                                 CAST(:permissions AS JSONB), NULL, NULL)"""),
            {"role_id": role_id, "permissions": json.dumps(permissions)},
        ).mappings().one()
        return row["out_changed_count"]

    def set_one(self, role_id: int, area: str, level: str) -> dict:
        row = self._db.execute(
            text("""CALL sp_set_role_permission(CAST(:role_id AS INTEGER), CAST(:area AS VARCHAR),
                                                CAST(:level AS VARCHAR), NULL, NULL, NULL, NULL)"""),
            {"role_id": role_id, "area": area, "level": level},
        ).mappings().one()
        return clean_out_row(row)

    def reset(self, role_id: int) -> int:
        row = self._db.execute(
            text("CALL sp_reset_role_permissions(CAST(:role_id AS INTEGER), NULL, NULL)"),
            {"role_id": role_id},
        ).mappings().one()
        return row["out_removed_count"]

    def has_permission(self, role_id: int, area: str, minimum: str) -> bool:
        return self._db.execute(
            text("""SELECT sp_has_role_permission(CAST(:role_id AS INTEGER),
                                                  CAST(:area AS VARCHAR), CAST(:minimum AS VARCHAR))"""),
            {"role_id": role_id, "area": area, "minimum": minimum},
        ).scalar_one()
