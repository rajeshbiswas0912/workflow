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
