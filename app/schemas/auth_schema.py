from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    is_temporary_password: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str
