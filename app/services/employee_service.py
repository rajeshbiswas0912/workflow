from sqlalchemy.orm import Session

from app.config.settings import settings
from app.enums.employee import EmployeeStatus
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeList, EmployeeListItem, EmployeeResponse, EmployeeUpdate
from app.utils.db_errors import db_errors
from app.utils.exceptions import ForbiddenError, NotFoundError
from app.utils.security import hash_password

UPDATABLE = ("first_name", "last_name", "email", "phone", "status", "department_id",
             "job_title", "reports_to_id", "hire_date", "monthly_salary", "role_id")

class EmployeeService:
    def __init__(self, db: Session, repo: EmployeeRepository):
        self._db = db
        self._repo = repo

    def list_employees(self, search: str | None, department_id: int | None, role_id: int | None,
                        status: EmployeeStatus | None, include_deleted: bool,
                        limit: int, offset: int) -> EmployeeList:
        with db_errors(self._db):
            rows = self._repo.list_all(search, department_id, role_id,
                                        status.value if status else None,
                                        include_deleted, limit, offset)
        return EmployeeList(
            items=[EmployeeListItem(**r) for r in rows],
            total=rows[0]["total_count"] if rows else 0,
            limit=limit,
            offset=offset,
        )

    def get_employee(self, employee_id: int, include_deleted: bool = False) -> EmployeeResponse:
        with db_errors(self._db):
            row = self._repo.get_by_id(employee_id, include_deleted)
        if row is None:
            raise NotFoundError(f"Employee with ID {employee_id} not found")
        return EmployeeResponse.model_validate(row)

    def create_employee(self, data: EmployeeCreate, actor: EmployeeResponse) -> EmployeeResponse:
        self._assert_can_touch_admin(actor, data.role_id)
        with db_errors(self._db):
            new_id = self._repo.create(
                first_name=data.first_name, last_name=data.last_name, email=data.email,
                phone=data.phone, status=data.status.value, department_id=data.department_id,
                job_title=data.job_title, reports_to_id=data.reports_to_id, hire_date=data.hire_date,
                monthly_salary=data.monthly_salary, role_id=data.role_id,
                temporary_password_hash=hash_password(data.temporary_password),
            )
            self._db.commit()
        return self.get_employee(new_id)

    def update_employee(self, employee_id: int, data: EmployeeUpdate, actor: EmployeeResponse) -> EmployeeResponse:
        with db_errors(self._db):
            current = self._repo.get_by_id(employee_id)
            if current is None:
                raise NotFoundError(f"Employee with ID {employee_id} not found")

            # sp_employee_update overwrites every field, so merge with the current values
            sent = data.model_fields_set
            merged = {f: getattr(data, f) if f in sent else current[f] for f in UPDATABLE}
            merged["status"] = getattr(merged["status"], "value", merged["status"])

            self._assert_can_touch_admin(actor, current["role_id"])
            self._assert_can_touch_admin(actor, merged["role_id"])
            if employee_id == actor.id and merged["role_id"] != current["role_id"]:
                raise ForbiddenError("You can't change your own role")

            self._repo.update(employee_id, **merged)
            if data.new_password:
                self._repo.reset_password(employee_id, hash_password(data.new_password))
            self._db.commit()
        return self.get_employee(employee_id)

    def change_status(self, employee_id: int, status: EmployeeStatus, actor: EmployeeResponse) -> EmployeeResponse:
        with db_errors(self._db):
            self._assert_can_manage(employee_id, actor)
            self._repo.change_status(employee_id, status.value)
            self._db.commit()
        return self.get_employee(employee_id)

    def delete_employee(self, employee_id: int, actor: EmployeeResponse) -> None:
        with db_errors(self._db):
            self._assert_can_manage(employee_id, actor)
            self._repo.delete(employee_id)
            self._db.commit()

    def restore_employee(self, employee_id: int, actor: EmployeeResponse) -> EmployeeResponse:
        with db_errors(self._db):
            self._repo.restore(employee_id)
            self._db.commit()
        return self.get_employee(employee_id)

    @staticmethod
    def _assert_can_touch_admin(actor: EmployeeResponse, role_id: int) -> None:
        if actor.role_id != settings.ADMIN_ROLE_ID and role_id == settings.ADMIN_ROLE_ID:
            raise ForbiddenError("Only an Admin can assign the Admin role or change Admin accounts")

    def _assert_can_manage(self, employee_id: int, actor: EmployeeResponse) -> None:
        """Used for status change and delete: the target must exist, and can't be yourself or an Admin."""
        target = self._repo.get_by_id(employee_id)
        if target is None:
            raise NotFoundError(f"Employee with ID {employee_id} not found")
        if employee_id == actor.id:
            raise ForbiddenError("You can't change the status of, or delete, your own account")
        self._assert_can_touch_admin(actor, target["role_id"])
