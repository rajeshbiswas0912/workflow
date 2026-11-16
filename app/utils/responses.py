from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

from app.schemas.common import ErrorResponse
from app.utils.exceptions import AppException

def _error_response(
    status_code: int,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(ErrorResponse(message=message)),
        headers=headers,
    )

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return _error_response(exc.status_code, exc.message, exc.headers)

async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return _error_response(
        exc.status_code, str(exc.detail), getattr(exc, "headers", None)
    )

async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"][1:])
        parts.append(f"{field}: {err['msg']}" if field else err["msg"])
    return _error_response(422, "; ".join(parts) or "Validation failed")

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(500, "Internal server error")

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
