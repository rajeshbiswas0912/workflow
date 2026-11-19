import re
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.enums.employee import EmployeeStatus

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

# --- Create Schema ---
class EmployeeCreate(BaseModel):
    # Personal details
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)

    # Job details
    department_id: int = Field(gt=0)
    job_title: str = Field(min_length=1, max_length=100)
    reports_to_id: int | None = Field(default=None, gt=0)
    hire_date: date
    monthly_salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    status: EmployeeStatus = EmployeeStatus.ACTIVE

    # System access
    role_id: int = Field(gt=0)
    temporary_password: str = Field(min_length=10, max_length=255)

    @field_validator("first_name", "last_name", "job_title")
    @classmethod
    def _strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\s+", "", value.strip())
        if not digits:
            return None
        if not re.fullmatch(r"\d{10}", digits):
            raise ValueError("Enter a 10-digit mobile number.")
        return digits

# --- Update Schema ---
class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    department_id: int | None = Field(default=None, gt=0)
    job_title: str | None = Field(default=None, min_length=1, max_length=100)
    reports_to_id: int | None = Field(default=None, gt=0)
    hire_date: date | None = None
    monthly_salary: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    status: EmployeeStatus | None = None
    role_id: int | None = Field(default=None, gt=0)
    is_temporary_password: bool | None = None

    @field_validator("first_name", "last_name", "job_title")
    @classmethod
    def _strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Field must not be blank")
        return value

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\s+", "", value.strip())
        if not digits:
            return None
        if not re.fullmatch(r"\d{10}", digits):
            raise ValueError("Enter a 10-digit mobile number.")
        return digits

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
