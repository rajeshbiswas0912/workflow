import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator, model_validator

from app.enums.employee import EmployeeStatus
from app.schemas.common import UTCDateTime

class DepartmentSummary(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class RoleSummary(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class ManagerSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: str

    model_config = ConfigDict(from_attributes=True)

# --- Response Schema ---
class EmployeeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    status: EmployeeStatus
    department_id: int
    job_title: str
    reports_to_id: int | None
    hire_date: date
    monthly_salary: Decimal
    role_id: int
    is_temporary_password: bool
    department: DepartmentSummary | None = None
    role: RoleSummary | None = None
    manager: ManagerSummary | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @computed_field
    @property
    def status_label(self) -> str:
        return self.status.label

    model_config = ConfigDict(from_attributes=True)

# --- Optional Delete Response Schema ---
class EmployeeDeleteResponse(BaseModel):
    message: str = "Employee deleted successfully"
    id: int


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)
    department_id: int
    job_title: str = Field(..., min_length=1, max_length=100)
    reports_to_id: int | None = None
    hire_date: date
    monthly_salary: Decimal = Field(..., ge=0, lt=10_000_000_000)
    status: str = "Active"
    role_id: int

class EmployeeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    department_id: int
    job_title: str = Field(min_length=1, max_length=100)
    reports_to_id: int | None = None
    hire_date: date
    monthly_salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    role_id: int
    temporary_password: str = Field(min_length=10, max_length=72)   # 72 = bcrypt limit


_NOT_NULL = ("first_name", "last_name", "email", "status", "department_id",
             "job_title", "hire_date", "monthly_salary", "role_id")

class EmployeeUpdate(BaseModel):
    """Omitted field = keep current value. null clears phone and reports_to_id only."""
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    status: EmployeeStatus | None = None
    department_id: int | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=100)
    reports_to_id: int | None = None
    hire_date: date | None = None
    monthly_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    role_id: int | None = None
    new_password: str | None = Field(default=None, min_length=10, max_length=72)

    @field_validator("new_password", mode="before")
    @classmethod
    def blank_password_means_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for f in _NOT_NULL:
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} can't be null")
        return self

class EmployeeStatusUpdate(BaseModel):
    status: EmployeeStatus

class EmployeeListItem(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    status: EmployeeStatus
    department_id: int
    department_name: str | None = None
    job_title: str
    reports_to_id: int | None = None
    hire_date: date
    role_id: int
    role_name: str | None = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    deleted_at: UTCDateTime | None = None

    @computed_field
    @property
    def status_label(self) -> str:
        return self.status.value.replace("_", " ").capitalize()

class EmployeeList(BaseModel):
    items: list[EmployeeListItem]
    total: int
    limit: int
    offset: int

class SetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match")
        return self
