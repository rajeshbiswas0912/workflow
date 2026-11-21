from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session


class ProductRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self, search, category, is_active, min_price, max_price, in_stock_only,
                 include_deleted, limit, offset) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_product_list(
                        CAST(:search AS TEXT), CAST(:category AS TEXT), CAST(:is_active AS BOOLEAN),
                        CAST(:min_price AS NUMERIC), CAST(:max_price AS NUMERIC),
                        CAST(:in_stock_only AS BOOLEAN), CAST(:include_deleted AS BOOLEAN),
                        CAST(:limit AS INT), CAST(:offset AS INT))"""),
            {"search": search, "category": category, "is_active": is_active, "min_price": min_price,
             "max_price": max_price, "in_stock_only": in_stock_only, "include_deleted": include_deleted,
             "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]

    def get_by_id(self, product_id: int, include_deleted: bool = False) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_product_get(CAST(:id AS BIGINT), CAST(:include_deleted AS BOOLEAN))"),
            {"id": product_id, "include_deleted": include_deleted},
        ).mappings().first()
        return dict(row) if row else None

    def get_by_sku(self, sku: str) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_product_get_by_sku(CAST(:sku AS TEXT))"), {"sku": sku},
        ).mappings().first()
        return dict(row) if row else None

    def summary(self, low_stock_threshold: int) -> dict:
        row = self._db.execute(
            text("SELECT * FROM fn_product_summary(CAST(:t AS INT))"), {"t": low_stock_threshold},
        ).mappings().one()
        return dict(row)

    def create(self, name, sku, category, description, unit_price, stock_quantity, is_active) -> int:
        row = self._db.execute(
            text("""CALL sp_product_create(CAST(NULL AS BIGINT), CAST(:name AS TEXT), CAST(:sku AS TEXT),
                                           CAST(:category AS TEXT), CAST(:description AS TEXT),
                                           CAST(:unit_price AS NUMERIC), CAST(:stock_quantity AS INT),
                                           CAST(:is_active AS BOOLEAN))"""),
            {"name": name, "sku": sku, "category": category, "description": description,
             "unit_price": unit_price, "stock_quantity": stock_quantity, "is_active": is_active},
        ).mappings().one()
        return row["p_id"]

    def update(self, product_id, name, sku, category, description, unit_price, is_active) -> None:
        self._db.execute(
            text("""CALL sp_product_update(CAST(:id AS BIGINT), CAST(:name AS TEXT), CAST(:sku AS TEXT),
                                           CAST(:category AS TEXT), CAST(:description AS TEXT),
                                           CAST(:unit_price AS NUMERIC), CAST(:is_active AS BOOLEAN))"""),
            {"id": product_id, "name": name, "sku": sku, "category": category,
             "description": description, "unit_price": unit_price, "is_active": is_active},
        )

    def set_active(self, product_id: int, is_active: bool) -> None:
        self._db.execute(
            text("CALL sp_product_set_active(CAST(:id AS BIGINT), CAST(:is_active AS BOOLEAN))"),
            {"id": product_id, "is_active": is_active},
        )

    def set_stock(self, product_id: int, stock_quantity: int) -> None:
        self._db.execute(
            text("CALL sp_product_set_stock(CAST(:id AS BIGINT), CAST(:qty AS INT))"),
            {"id": product_id, "qty": stock_quantity},
        )

    def adjust_stock(self, product_id: int, delta: int) -> None:
        self._db.execute(
            text("CALL sp_product_adjust_stock(CAST(:id AS BIGINT), CAST(:delta AS INT))"),
            {"id": product_id, "delta": delta},
        )

    def delete(self, product_id: int) -> None:
        self._db.execute(text("CALL sp_product_delete(CAST(:id AS BIGINT))"), {"id": product_id})

    def restore(self, product_id: int) -> None:
        self._db.execute(text("CALL sp_product_restore(CAST(:id AS BIGINT))"), {"id": product_id})

    def categories(self) -> list[dict]:
        rows = self._db.execute(text("SELECT * FROM fn_product_categories()")).mappings().all()
        return [dict(r) for r in rows]
