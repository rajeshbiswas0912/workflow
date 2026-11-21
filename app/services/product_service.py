from decimal import Decimal

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.repositories.product_repository import ProductRepository
from app.schemas.product import BestSeller, ProductCategory, ProductCreate, ProductItem, ProductList, ProductStats, ProductUpdate
from app.utils.db_errors import db_errors
from app.utils.exceptions import NotFoundError


DETAIL_FIELDS = ("name", "sku", "category", "description", "unit_price", "is_active")


class ProductService:
    def __init__(self, db: Session, repo: ProductRepository):
        self._db = db
        self._repo = repo

    # ---------- reads ----------
    def list_products(self, search, category, is_active, min_price, max_price, in_stock_only,
                      include_deleted, limit, offset) -> ProductList:
        with db_errors(self._db):
            rows = self._repo.list_all(search, category, is_active, min_price, max_price,
                                       in_stock_only, include_deleted, limit, offset)
        return ProductList(
            items=[ProductItem(**r) for r in rows],
            total=rows[0]["total_count"] if rows else 0,
            limit=limit,
            offset=offset,
        )

    def get_product(self, product_id: int, include_deleted: bool = False) -> ProductItem:
        with db_errors(self._db):
            row = self._repo.get_by_id(product_id, include_deleted)
        if row is None:
            raise NotFoundError(f"Product with ID {product_id} not found")
        return ProductItem(**row)

    def get_product_by_sku(self, sku: str) -> ProductItem:
        with db_errors(self._db):
            row = self._repo.get_by_sku(sku)
        if row is None:
            raise NotFoundError("No product with that SKU")
        return ProductItem(**row)

    def stats(self, low_stock_threshold: int = settings.LOW_STOCK_THRESHOLD) -> ProductStats:
        with db_errors(self._db):
            row = self._repo.summary(low_stock_threshold)
        best = None
        if row["best_seller_id"] is not None:
            best = BestSeller(id=row["best_seller_id"], name=row["best_seller_name"],
                              units_sold=row["best_seller_units"], total_sales=row["best_seller_sales"])
        return ProductStats(
            total=row["total_count"], active=row["active_count"], discontinued=row["discontinued_count"],
            low_stock=row["low_stock_count"], stock_value=row["stock_value"],
            low_stock_threshold=low_stock_threshold, best_seller=best,
        )

    # ---------- writes ----------
    def create_product(self, data: ProductCreate) -> ProductItem:
        with db_errors(self._db):
            new_id = self._repo.create(data.name, data.sku, data.category, data.description,
                                       data.unit_price, data.stock_quantity, data.is_active)
            self._db.commit()
        return self.get_product(new_id)

    def update_product(self, product_id: int, data: ProductUpdate) -> ProductItem:
        with db_errors(self._db):
            current = self._repo.get_by_id(product_id)
            if current is None:
                raise NotFoundError(f"Product with ID {product_id} not found")

            # sp_product_update overwrites these five fields, so merge with the current values
            sent = data.model_fields_set
            merged = {f: getattr(data, f) if f in sent else current[f] for f in DETAIL_FIELDS}
            self._repo.update(product_id, **merged)

            # stock has its own procedure; only touch it when the value really changes
            if data.stock_quantity is not None and data.stock_quantity != current["stock_quantity"]:
                self._repo.set_stock(product_id, data.stock_quantity)
            self._db.commit()
        return self.get_product(product_id)

    def set_active(self, product_id: int, is_active: bool) -> ProductItem:
        with db_errors(self._db):
            self._repo.set_active(product_id, is_active)
            self._db.commit()
        return self.get_product(product_id)

    def set_stock(self, product_id: int, stock_quantity: int) -> ProductItem:
        with db_errors(self._db):
            self._repo.set_stock(product_id, stock_quantity)
            self._db.commit()
        return self.get_product(product_id)

    def adjust_stock(self, product_id: int, delta: int) -> ProductItem:
        with db_errors(self._db):
            self._repo.adjust_stock(product_id, delta)
            self._db.commit()
        return self.get_product(product_id)

    def delete_product(self, product_id: int) -> None:
        with db_errors(self._db):
            self._repo.delete(product_id)
            self._db.commit()

    def restore_product(self, product_id: int) -> ProductItem:
        with db_errors(self._db):
            self._repo.restore(product_id)
            self._db.commit()
        return self.get_product(product_id)

    def list_categories(self) -> list[ProductCategory]:
        with db_errors(self._db):
            rows = self._repo.categories()
        return [ProductCategory(name=r["category"], product_count=r["product_count"]) for r in rows]
