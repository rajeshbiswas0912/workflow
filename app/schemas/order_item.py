from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class OrderProductSummary(BaseModel):
    id: int
    name: str
    sku: str | None = None

    model_config = ConfigDict(from_attributes=True)

class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product: OrderProductSummary | None = None

    model_config = ConfigDict(from_attributes=True)
