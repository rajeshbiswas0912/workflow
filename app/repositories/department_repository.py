from sqlalchemy import text
from sqlalchemy.orm import Session


class DepartmentRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self, search: str | None, include_deleted: bool, limit: int, offset: int) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_department_list(
                        CAST(:search AS TEXT), CAST(:include_deleted AS BOOLEAN),
                        CAST(:limit AS INT), CAST(:offset AS INT))"""),
            {"search": search, "include_deleted": include_deleted, "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, department_id: int, include_deleted: bool = False) -> dict | None:
        row = self._db.execute(
            text("""SELECT * FROM fn_department_get(
                        CAST(:id AS BIGINT), CAST(:include_deleted AS BOOLEAN))"""),
            {"id": department_id, "include_deleted": include_deleted},
        ).mappings().first()
        return dict(row) if row else None

    def create(self, name: str, description: str | None, head_id: int | None) -> int:
        row = self._db.execute(
            text("""CALL sp_department_create(CAST(NULL AS BIGINT), CAST(:name AS TEXT),
                                                CAST(:description AS TEXT), CAST(:head_id AS BIGINT))"""),
            {"name": name, "description": description, "head_id": head_id},
        ).mappings().one()
        return row["p_id"]

    def update(self, department_id: int, name: str, description: str | None, head_id: int | None) -> None:
        self._db.execute(
            text("""CALL sp_department_update(CAST(:id AS BIGINT), CAST(:name AS TEXT),
                                                CAST(:description AS TEXT), CAST(:head_id AS BIGINT))"""),
            {"id": department_id, "name": name, "description": description, "head_id": head_id},
        )

    def set_head(self, department_id: int, head_id: int | None) -> None:
        self._db.execute(
            text("CALL sp_department_set_head(CAST(:id AS BIGINT), CAST(:head_id AS BIGINT))"),
            {"id": department_id, "head_id": head_id},
        )

    def delete(self, department_id: int) -> None:
        self._db.execute(text("CALL sp_department_delete(CAST(:id AS BIGINT))"), {"id": department_id})

    def restore(self, department_id: int) -> None:
        self._db.execute(text("CALL sp_department_restore(CAST(:id AS BIGINT))"), {"id": department_id})
