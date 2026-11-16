from typing import Any

class AppException(Exception):

    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "Internal server error"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = 400
    code = "bad_request"
    default_message = "Bad request"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"
    default_message = "Not authenticated"

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        super().__init__(
            message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"
    default_message = "You do not have permission to perform this action"


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    default_message = "Resource already exists"
