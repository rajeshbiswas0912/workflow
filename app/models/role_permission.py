from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.enums.permission import PermissionArea, PermissionLevel

if TYPE_CHECKING:
    from app.models.role import Role

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    area: Mapped[PermissionArea] = mapped_column(
        Enum(
            PermissionArea,
            name="permission_area_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        primary_key=True,
    )
    access_level: Mapped[PermissionLevel] = mapped_column(
        Enum(
            PermissionLevel,
            name="permission_level_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PermissionLevel.none,
        server_default=PermissionLevel.none.value,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )

    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
