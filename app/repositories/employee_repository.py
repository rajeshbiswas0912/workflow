from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.base import Row, fetch_one

class EmployeeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_email(self, email: str) -> Row | None:
        return fetch_one(
            self._db,
            "SELECT * FROM fn_employee_get_auth(:email)",
            {"email": email},
        )

    # def get_by_id(self, id: int) -> Row | None:
    #     return fetch_one(
    #         self._db,
    #         "SELECT * FROM fn_employee_get(:id)",
    #         {"id": id},
    #     )

    def get_by_id(self, employee_id: int, include_deleted: bool = False) -> dict | None:
        row = self._db.execute(
            text("SELECT * FROM fn_employee_get(CAST(:id AS BIGINT), CAST(:include_deleted AS BOOLEAN))"),
            {"id": employee_id, "include_deleted": include_deleted},
        ).mappings().first()
        return dict(row) if row else None

    def list_all(self, search: str | None, department_id: int | None, role_id: int | None,
                    status: str | None, include_deleted: bool, limit: int, offset: int) -> list[dict]:
        rows = self._db.execute(
            text("""SELECT * FROM fn_employee_list(
                        CAST(:search AS TEXT), CAST(:department_id AS BIGINT), CAST(:role_id AS BIGINT),
                        CAST(:status AS TEXT), CAST(:include_deleted AS BOOLEAN),
                        CAST(:limit AS INT), CAST(:offset AS INT))"""),
            {"search": search, "department_id": department_id, "role_id": role_id, "status": status,
                "include_deleted": include_deleted, "limit": limit, "offset": offset},
        ).mappings().all()
        return [dict(r) for r in rows]

    def create(self, *, first_name: str, last_name: str, email: str, phone: str | None, status: str,
                department_id: int, job_title: str, reports_to_id: int | None, hire_date: date,
                monthly_salary: Decimal, role_id: int, temporary_password_hash: str) -> int:
        row = self._db.execute(
            text("""CALL sp_employee_create(
                        CAST(NULL AS BIGINT), CAST(:first_name AS TEXT), CAST(:last_name AS TEXT),
                        CAST(:email AS TEXT), CAST(:phone AS TEXT), CAST(:status AS TEXT),
                        CAST(:department_id AS BIGINT), CAST(:job_title AS TEXT),
                        CAST(:reports_to_id AS BIGINT), CAST(:hire_date AS DATE),
                        CAST(:monthly_salary AS NUMERIC), CAST(:role_id AS BIGINT),
                        CAST(:temporary_password_hash AS TEXT))"""),
            {"first_name": first_name, "last_name": last_name, "email": email, "phone": phone,
                "status": status, "department_id": department_id, "job_title": job_title,
                "reports_to_id": reports_to_id, "hire_date": hire_date, "monthly_salary": monthly_salary,
                "role_id": role_id, "temporary_password_hash": temporary_password_hash},
        ).mappings().one()
        return row["p_id"]

    def update(self, employee_id: int, *, first_name: str, last_name: str, email: str, phone: str | None,
                status: str, department_id: int, job_title: str, reports_to_id: int | None,
                hire_date: date, monthly_salary: Decimal, role_id: int) -> None:
        self._db.execute(
            text("""CALL sp_employee_update(
                        CAST(:id AS BIGINT), CAST(:first_name AS TEXT), CAST(:last_name AS TEXT),
                        CAST(:email AS TEXT), CAST(:phone AS TEXT), CAST(:status AS TEXT),
                        CAST(:department_id AS BIGINT), CAST(:job_title AS TEXT),
                        CAST(:reports_to_id AS BIGINT), CAST(:hire_date AS DATE),
                        CAST(:monthly_salary AS NUMERIC), CAST(:role_id AS BIGINT))"""),
            {"id": employee_id, "first_name": first_name, "last_name": last_name, "email": email,
                "phone": phone, "status": status, "department_id": department_id, "job_title": job_title,
                "reports_to_id": reports_to_id, "hire_date": hire_date, "monthly_salary": monthly_salary,
                "role_id": role_id},
        )

    def change_status(self, employee_id: int, status: str) -> None:
        self._db.execute(
            text("CALL sp_employee_change_status(CAST(:id AS BIGINT), CAST(:status AS TEXT))"),
            {"id": employee_id, "status": status},
        )

    def delete(self, employee_id: int) -> None:
        self._db.execute(text("CALL sp_employee_delete(CAST(:id AS BIGINT))"), {"id": employee_id})

    def restore(self, employee_id: int) -> None:
        self._db.execute(text("CALL sp_employee_restore(CAST(:id AS BIGINT))"), {"id": employee_id})

    def reset_password(self, employee_id: int, temporary_password_hash: str) -> None:
        self._db.execute(
            text("CALL sp_employee_reset_password(CAST(:id AS BIGINT), CAST(:hash AS TEXT))"),
            {"id": employee_id, "hash": temporary_password_hash},
        )
