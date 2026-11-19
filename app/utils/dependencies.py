from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.repositories.employee_repository import EmployeeRepository
from app.services.auth_service import AuthService

def get_employee_repository(db: Session = Depends(get_db)) -> EmployeeRepository:
    return EmployeeRepository(db)

def get_auth_service(
    repo: EmployeeRepository = Depends(get_employee_repository),
) -> AuthService:
    return AuthService(repo)
