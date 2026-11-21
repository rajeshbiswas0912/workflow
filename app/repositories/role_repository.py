from sqlalchemy import text
from sqlalchemy.orm import Session
from app.utils.helpers import clean_out_row

class RoleRepository:
    def __init__(self, db: Session):
        self._db = db

    def create(self, name: str, is_active: bool) -> dict:
        row = self._db.execute(
            text("""CALL sp_create_role(CAST(:name AS VARCHAR), CAST(:is_active AS BOOLEAN),
                                        NULL, NULL, NULL, NULL, NULL, NULL)"""),
            {"name": name, "is_active": is_active},
        ).mappings().one()
        return clean_out_row(row)

    def update(self, role_id: int, name: str | None, is_active: bool | None) -> dict:
        row = self._db.execute(
            text("""CALL sp_update_role(CAST(:id AS INTEGER), CAST(:name AS VARCHAR),
                                        CAST(:is_active AS BOOLEAN),
                                        NULL, NULL, NULL, NULL, NULL, NULL)"""),
            {"id": role_id, "name": name, "is_active": is_active},
        ).mappings().one()
        return clean_out_row(row)
