from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Enum, ForeignKey, Date, Numeric, Boolean, DateTime, text
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import TYPE_CHECKING

from app.config.database import Base
from app.enums.employee import EmployeeStatus

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.role import Role
    from app.models.order import Order

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(
            EmployeeStatus,
            name="employee_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=EmployeeStatus.ACTIVE,
        nullable=False
    )

    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    reports_to_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("employees.id"), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    temporary_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_temporary_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    department: Mapped["Department"] = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
    )
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="employees",
    )
    manager: Mapped["Employee | None"] = relationship(
        "Employee",
        remote_side=[id],
        back_populates="subordinates",
    )
    subordinates: Mapped[list["Employee"]] = relationship(
        "Employee",
        back_populates="manager",
    )
    handled_orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="handled_by",
        foreign_keys="[Order.handled_by_id]",
    )
