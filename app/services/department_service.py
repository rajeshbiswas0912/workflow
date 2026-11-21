from sqlalchemy.orm import Session

from app.repositories.department_repository import DepartmentRepository
from app.schemas.department import DepartmentCreate, DepartmentItem, DepartmentList, DepartmentUpdate
from app.utils.db_errors import db_errors
from app.utils.exceptions import NotFoundError


class DepartmentService:
    def __init__(self, db: Session, repo: DepartmentRepository):
        self._db = db
        self._repo = repo

    def list_departments(self, search: str | None, include_deleted: bool, limit: int, offset: int) -> DepartmentList:
        with db_errors(self._db):
            rows = self._repo.list_all(search, include_deleted, limit, offset)
        return DepartmentList(
            items=[DepartmentItem(**r) for r in rows],
            total=rows[0]["total_count"] if rows else 0,
            total_employees=rows[0]["total_employees"] if rows else 0,
            limit=limit,
            offset=offset,
        )

    def get_department(self, department_id: int, include_deleted: bool = False) -> DepartmentItem:
        with db_errors(self._db):
            row = self._repo.get_by_id(department_id, include_deleted)
        if row is None:
            raise NotFoundError(f"Department with ID {department_id} not found")
        return DepartmentItem(**row)

    def create_department(self, data: DepartmentCreate) -> DepartmentItem:
        with db_errors(self._db):
            new_id = self._repo.create(data.name, data.description, data.department_head_id)
            self._db.commit()
        return self.get_department(new_id)

    def update_department(self, department_id: int, data: DepartmentUpdate) -> DepartmentItem:
        with db_errors(self._db):
            current = self._repo.get_by_id(department_id)
            if current is None:
                raise NotFoundError(f"Department with ID {department_id} not found")

            fields = data.model_fields_set
            name = data.name if data.name is not None else current["name"]
            description = data.description if "description" in fields else current["description"]
            head_id = data.department_head_id if "department_head_id" in fields else current["department_head_id"]

            self._repo.update(department_id, name, description, head_id)
            self._db.commit()
        return self.get_department(department_id)

    def set_head(self, department_id: int, employee_id: int | None) -> DepartmentItem:
        with db_errors(self._db):
            self._repo.set_head(department_id, employee_id)
            self._db.commit()
        return self.get_department(department_id)

    def delete_department(self, department_id: int) -> None:
        with db_errors(self._db):
            self._repo.delete(department_id)
            self._db.commit()

    def restore_department(self, department_id: int) -> DepartmentItem:
        with db_errors(self._db):
            self._repo.restore(department_id)
            self._db.commit()
        return self.get_department(department_id)
