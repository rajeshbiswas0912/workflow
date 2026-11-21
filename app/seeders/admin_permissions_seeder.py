from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.enums.permission import PermissionArea, PermissionLevel
from app.models.role import Role
from app.models.role_permission import RolePermission
import app.models

ADMIN_ROLE_ID = 1


def seed_admin_permissions(db: Session) -> int:
    """Give the Admin role (id 1) full access to every area. Safe to run repeatedly."""
    role = db.get(Role, ADMIN_ROLE_ID)
    if role is None or role.deleted_at is not None:
        raise RuntimeError(f"Role with ID {ADMIN_ROLE_ID} not found. Seed the roles first.")
    if role.name.strip().lower() != "admin":
        raise RuntimeError(f"Role {ADMIN_ROLE_ID} is '{role.name}', not 'Admin'. Check your role seed.")

    rows = [
        {"role_id": ADMIN_ROLE_ID, "area": area, "access_level": PermissionLevel.full}
        for area in PermissionArea
    ]

    stmt = insert(RolePermission).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["role_id", "area"],
        set_={
            "access_level": stmt.excluded.access_level,
            "updated_at": func.timezone("utc", func.now()),
        },
    )
    db.execute(stmt)
    db.commit()
    return len(rows)


if __name__ == "__main__":
    from app.config.database import SessionLocal

    with SessionLocal() as db:
        count = seed_admin_permissions(db)
        print(f"Admin permissions seeded: {count} areas set to full")
