from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.config.settings import settings
from app.schemas.common import UTCDateTime

class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    sku: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000_000)
    is_active: bool = True
    category: str = Field(min_length=1, max_length=100)


class ProductUpdate(BaseModel):
    """Omitted field = keep current value. null clears description only."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=150)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None
    # Send only if the user actually edited it (see the note on stale forms below)
    stock_quantity: int | None = Field(default=None, ge=0, le=1_000_000_000)
    category: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for f in ("name", "sku", "unit_price", "is_active", "stock_quantity"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} can't be null")
        return self


class ProductStatusUpdate(BaseModel):
    is_active: bool


class ProductStockSet(BaseModel):
    stock_quantity: int = Field(ge=0, le=1_000_000_000)


class ProductStockAdjust(BaseModel):
    delta: int = Field(ge=-1_000_000_000, le=1_000_000_000)

    @field_validator("delta")
    @classmethod
    def non_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("delta must be a non-zero number")
        return v


class ProductItem(BaseModel):
    id: int
    name: str
    sku: str | None = None
    description: str | None = None
    unit_price: Decimal
    stock_quantity: int
    is_active: bool
    units_sold: int = 0
    total_sales: Decimal = Decimal("0.00")
    category: str | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    deleted_at: UTCDateTime | None = None

    @computed_field
    @property
    def is_low_stock(self) -> bool:
        return self.is_active and self.stock_quantity < settings.LOW_STOCK_THRESHOLD


class ProductList(BaseModel):
    items: list[ProductItem]
    total: int
    limit: int
    offset: int

class BestSeller(BaseModel):
    id: int
    name: str
    units_sold: int
    total_sales: Decimal

class ProductStats(BaseModel):
    total: int
    active: int
    discontinued: int
    low_stock: int
    stock_value: Decimal
    low_stock_threshold: int
    best_seller: BestSeller | None = None

class ProductCategory(BaseModel):
    name: str
    product_count: int
