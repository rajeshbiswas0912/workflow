from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session


class OrderRepository:
    def __init__(self, db: Session):
        self._db = db

    # ---------- orders ----------
    def list_all(self, search: str | None, customer_id: int | None, handled_by_id: int | None,
                 status: str | None, date_from: date | None, date_to: date | None,
                 include_deleted: bool, limit: int, offset: int) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_order_list(
                        CAST(:search AS TEXT), CAST(:customer_id AS BIGINT), CAST(:handled_by_id AS BIGINT),
                        CAST(:status AS TEXT), CAST(:date_from AS DATE), CAST(:date_to AS DATE),
                        CAST(:include_deleted AS BOOLEAN), CAST(:limit AS INT), CAST(:offset AS INT))"""),
            {"search": search, "customer_id": customer_id, "handled_by_id": handled_by_id, "status": status,
             "date_from": date_from, "date_to": date_to, "include_deleted": include_deleted,
             "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]

    def status_counts(self, search: str | None, customer_id: int | None, handled_by_id: int | None,
                      date_from: date | None, date_to: date | None) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_order_status_counts(
                        CAST(:search AS TEXT), CAST(:customer_id AS BIGINT), CAST(:handled_by_id AS BIGINT),
                        CAST(:date_from AS DATE), CAST(:date_to AS DATE))"""),
            {"search": search, "customer_id": customer_id, "handled_by_id": handled_by_id,
             "date_from": date_from, "date_to": date_to},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, order_id: int, include_deleted: bool = False) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_order_get(CAST(:id AS BIGINT), CAST(:include_deleted AS BOOLEAN))"),
            {"id": order_id, "include_deleted": include_deleted},
        ).mappings().first()
        return dict(row) if row else None

    def get_by_number(self, order_number: str) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_order_get_by_number(CAST(:n AS TEXT))"), {"n": order_number},
        ).mappings().first()
        return dict(row) if row else None

    def next_number(self) -> str:
        return self._db.execute(text("SELECT fn_order_next_number()")).scalar_one()

    def create(self, order_number: str, customer_id: int, handled_by_id: int, order_date: date,
               total_amount: Decimal, status: str, notes: str | None) -> int:
        row = self._db.execute(
            text("""CALL sp_order_create(CAST(NULL AS BIGINT), CAST(:number AS TEXT), CAST(:customer_id AS BIGINT),
                                         CAST(:handled_by_id AS BIGINT), CAST(:order_date AS DATE),
                                         CAST(:total AS NUMERIC), CAST(:status AS TEXT), CAST(:notes AS TEXT))"""),
            {"number": order_number, "customer_id": customer_id, "handled_by_id": handled_by_id,
             "order_date": order_date, "total": total_amount, "status": status, "notes": notes},
        ).mappings().one()
        return row["p_id"]

    def update(self, order_id: int, order_number: str, customer_id: int, handled_by_id: int,
               order_date: date, total_amount: Decimal, notes: str | None) -> None:
        self._db.execute(
            text("""CALL sp_order_update(CAST(:id AS BIGINT), CAST(:number AS TEXT), CAST(:customer_id AS BIGINT),
                                         CAST(:handled_by_id AS BIGINT), CAST(:order_date AS DATE),
                                         CAST(:total AS NUMERIC), CAST(:notes AS TEXT))"""),
            {"id": order_id, "number": order_number, "customer_id": customer_id,
             "handled_by_id": handled_by_id, "order_date": order_date, "total": total_amount, "notes": notes},
        )

    def change_status(self, order_id: int, status: str) -> None:
        self._db.execute(
            text("CALL sp_order_change_status(CAST(:id AS BIGINT), CAST(:status AS TEXT))"),
            {"id": order_id, "status": status},
        )

    def delete(self, order_id: int) -> None:
        self._db.execute(text("CALL sp_order_delete(CAST(:id AS BIGINT))"), {"id": order_id})

    def restore(self, order_id: int) -> None:
        self._db.execute(text("CALL sp_order_restore(CAST(:id AS BIGINT))"), {"id": order_id})

    # ---------- line items ----------
    def list_items(self, order_id: int) -> list[dict]:
        rows = self._db.execute(
            text("SELECT * FROM fn_order_item_list_by_order(CAST(:id AS BIGINT))"), {"id": order_id},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_item(self, item_id: int) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_order_item_get(CAST(:id AS BIGINT))"), {"id": item_id},
        ).mappings().first()
        return dict(row) if row else None

    def create_item(self, order_id: int, product_id: int, quantity: int, unit_price: Decimal) -> int:
        row = self._db.execute(
            text("""CALL sp_order_item_create(CAST(NULL AS BIGINT), CAST(:order_id AS BIGINT),
                                              CAST(:product_id AS BIGINT), CAST(:quantity AS INT),
                                              CAST(:unit_price AS NUMERIC))"""),
            {"order_id": order_id, "product_id": product_id, "quantity": quantity, "unit_price": unit_price},
        ).mappings().one()
        return row["p_id"]

    def update_item(self, item_id: int, product_id: int, quantity: int, unit_price: Decimal) -> None:
        self._db.execute(
            text("""CALL sp_order_item_update(CAST(:id AS BIGINT), CAST(:product_id AS BIGINT),
                                              CAST(:quantity AS INT), CAST(:unit_price AS NUMERIC))"""),
            {"id": item_id, "product_id": product_id, "quantity": quantity, "unit_price": unit_price},
        )

    def delete_item(self, item_id: int) -> None:
        self._db.execute(text("CALL sp_order_item_delete(CAST(:id AS BIGINT))"), {"id": item_id})
