from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, DateTime, String, text, func, true
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role_permission import RolePermission

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
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
    employees: Mapped[list["Employee"]] = relationship(
        "Employee",
        back_populates="role",
    )
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role",
        cascade="all, delete-orphan", passive_deletes=True,
    )
