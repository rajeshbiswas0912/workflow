from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UTCDateTime


class CustomerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=2000)


class CustomerUpdate(BaseModel):
    """Omitted field = keep current value. null clears phone, city and address."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for f in ("name", "email"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} can't be null")
        return self


class CustomerItem(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None
    city: str | None = None
    address: str | None = None
    order_count: int = 0
    total_spent: Decimal = Decimal("0.00")
    created_at: UTCDateTime
    updated_at: UTCDateTime
    deleted_at: UTCDateTime | None = None


class CustomerList(BaseModel):
    items: list[CustomerItem]
    total: int
    limit: int
    offset: int
