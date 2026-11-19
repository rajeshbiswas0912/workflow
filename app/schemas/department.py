from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    department_head_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    department_head_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DepartmentHeadSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: str

    model_config = ConfigDict(from_attributes=True)

class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: str | None
    department_head_id: int | None
    department_head: DepartmentHeadSummary | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DepartmentDeleteResponse(BaseModel):
    message: str = "Department deleted successfully"
    id: int
