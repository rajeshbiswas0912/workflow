from typing import Annotated, Any

from app.repositories.employee_repository import EmployeeRepository
from app.schemas.auth_schema import Token
from app.schemas.employee import EmployeeResponse
from app.utils.exceptions import ForbiddenError, UnauthorizedError
from app.utils.security import create_access_token, create_refresh_token, decode_token, get_dummy_hash, verify_password


class AuthService:
    def __init__(self, employee_repository: EmployeeRepository) -> None:
        self._employee = employee_repository

    def login(self, email: str, password: str) -> Token:
        row = self._employee.get_by_email(email.strip().lower())

        is_temp = bool(row and row["is_temporary_password"])
        stored_hash = (row["temporary_password"] if is_temp else row["password"]) if row else None
        password_ok = verify_password(password, stored_hash or get_dummy_hash())

        if row is None or not stored_hash or not password_ok or row["status"] != "active":
            raise UnauthorizedError("Incorrect email or password")

        token, expires_in = create_access_token(row["id"])
        refresh_token, refresh_expires_in = create_refresh_token(row["id"])
        return Token(
            access_token=token,
            expires_in=expires_in,
            refresh_token=refresh_token,
            refresh_expires_in=refresh_expires_in,
            is_temporary_password=is_temp
        )


    def refresh(self, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise UnauthorizedError("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")

        employee = self._employee.get_by_id(int(payload["sub"]))
        if employee is None or employee["deleted_at"] is not None:
            raise UnauthorizedError("Account not found or disabled")

        token, expires_in = create_access_token(employee["id"])
        refresh_token, refresh_expires_in = create_refresh_token(employee["id"])

        return Token(
            access_token=token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_expires_in=refresh_expires_in,
        )

    def get_current_user(self, token: str) -> EmployeeResponse:
        try:
            payload = decode_token(token)
        except Exception:  # expired, bad signature, malformed
            raise UnauthorizedError("Invalid or expired token")

        # a refresh token must not work as an access token
        if payload.get("type") == "refresh":
            raise UnauthorizedError("Invalid token type")

        employee = self._employee.get_by_id(int(payload["sub"]))
        if employee is None or employee["deleted_at"] is not None:
            raise UnauthorizedError("Account not found or disabled")

        return EmployeeResponse.model_validate(dict(employee))
