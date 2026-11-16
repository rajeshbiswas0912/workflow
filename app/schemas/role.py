from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.schemas.common import UTCDateTime

class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: UTCDateTime
    updated_at: UTCDateTime
