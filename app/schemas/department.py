from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UTCDateTime


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    department_head_id: int | None = None


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    department_head_id: int | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one of: name, description, department_head_id")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name can't be null")
        return self


class DepartmentHeadUpdate(BaseModel):
    employee_id: int | None = None


class DepartmentItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    department_head_id: int | None = None
    head_name: str | None = None
    employee_count: int
    created_at: UTCDateTime
    updated_at: UTCDateTime
    deleted_at: UTCDateTime | None = None


class DepartmentList(BaseModel):
    items: list[DepartmentItem]
    total: int
    total_employees: int
    limit: int
    offset: int
