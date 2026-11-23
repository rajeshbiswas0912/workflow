"""Simple seeder: Department -> Role -> Admin employee.

Run from the project root:
    python -m app.seeders.seed_admin
"""
from datetime import date
from decimal import Decimal

from app.config.database import SessionLocal
from app.enums.employee import EmployeeStatus
from app.models.department import Department
from app.models.employee import Employee
from app.models.role import Role

# Import every model so SQLAlchemy can resolve all relationships (e.g. Employee -> Order).
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.utils.security import hash_password
from sqlalchemy import select
from app.config.settings import settings

ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD


def main() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Employee.id).where(Employee.email == ADMIN_EMAIL)):
            print("Admin already exists, skipping")
            return

        # 1. Department
        department = Department(name="Administration", description="Company administration")
        db.add(department)
        db.flush()

        # 2. Role
        role = Role(name="Admin")
        db.add(role)
        db.flush()

        # 3. Employee
        admin = Employee(
            first_name="System",
            last_name="Admin",
            email=ADMIN_EMAIL,
            status=EmployeeStatus.ACTIVE,
            department_id=department.id,
            job_title="System Administrator",
            hire_date=date.today(),
            monthly_salary=Decimal("0.00"),
            role_id=role.id,
            password=hash_password(ADMIN_PASSWORD),
            is_temporary_password=False,
        )
        db.add(admin)
        db.flush()

        # Make the admin the department head
        department.department_head_id = admin.id

        db.commit()
        print(f"Seeded department={department.id}, role={role.id}, admin={admin.id}")


if __name__ == "__main__":
    main()
