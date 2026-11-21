from sqlalchemy import text
from sqlalchemy.orm import Session


class CustomerRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self, search: str | None, city: str | None, include_deleted: bool,
                 limit: int, offset: int) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_customer_list(
                        CAST(:search AS TEXT), CAST(:city AS TEXT), CAST(:include_deleted AS BOOLEAN),
                        CAST(:limit AS INT), CAST(:offset AS INT))"""),
            {"search": search, "city": city, "include_deleted": include_deleted,
             "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, customer_id: int, include_deleted: bool = False) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_customer_get(CAST(:id AS BIGINT), CAST(:include_deleted AS BOOLEAN))"),
            {"id": customer_id, "include_deleted": include_deleted},
        ).mappings().first()
        return dict(row) if row else None

    def get_by_email(self, email: str) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_customer_get_by_email(CAST(:email AS TEXT))"),
            {"email": email},
        ).mappings().first()
        return dict(row) if row else None

    def create(self, name: str, email: str, phone: str | None, city: str | None, address: str | None) -> int:
        row = self._db.execute(
            text("""CALL sp_customer_create(CAST(NULL AS BIGINT), CAST(:name AS TEXT), CAST(:email AS TEXT),
                                            CAST(:phone AS TEXT), CAST(:city AS TEXT), CAST(:address AS TEXT))"""),
            {"name": name, "email": email, "phone": phone, "city": city, "address": address},
        ).mappings().one()
        return row["p_id"]

    def update(self, customer_id: int, name: str, email: str, phone: str | None,
               city: str | None, address: str | None) -> None:
        self._db.execute(
            text("""CALL sp_customer_update(CAST(:id AS BIGINT), CAST(:name AS TEXT), CAST(:email AS TEXT),
                                            CAST(:phone AS TEXT), CAST(:city AS TEXT), CAST(:address AS TEXT))"""),
            {"id": customer_id, "name": name, "email": email, "phone": phone, "city": city, "address": address},
        )

    def delete(self, customer_id: int) -> None:
        self._db.execute(text("CALL sp_customer_delete(CAST(:id AS BIGINT))"), {"id": customer_id})

    def restore(self, customer_id: int) -> None:
        self._db.execute(text("CALL sp_customer_restore(CAST(:id AS BIGINT))"), {"id": customer_id})
