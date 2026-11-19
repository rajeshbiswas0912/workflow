from typing import Annotated

from fastapi import APIRouter, Depends, Form

from app.schemas.auth_schema import Token
from app.schemas.common import ApiResponse, ErrorResponse
from app.services.auth_service import AuthService
from app.utils.dependencies import get_auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post(
    "/login",
    response_model=ApiResponse[Token],
    summary="Log in and get a JWT access token",
    responses={401: {"model": ErrorResponse}},
)
def login(
    username: Annotated[str, Form(description="Your email")],
    password: Annotated[str, Form()],
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[Token]:
    token = service.login(username, password)
    return ApiResponse(data=token, message="Login successful")
