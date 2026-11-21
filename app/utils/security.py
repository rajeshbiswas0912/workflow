from datetime import datetime, timedelta, timezone
from functools import lru_cache
import bcrypt
import jwt
from app.config.settings import settings


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # e.g. password longer than bcrypt's 72-byte limit, or malformed hash
        return False

@lru_cache
def get_dummy_hash() -> str:
    """Used to spend the same time on unknown emails as on wrong passwords,
    so login timing does not reveal which emails are registered."""
    return hash_password("timing-attack-protection")

def _create_token(sub: str, expires_seconds: int, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)

def create_access_token(user_id: int) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = _create_token(str(user_id), int(expires_delta.total_seconds()), "access")
    return token, int(expires_delta.total_seconds())

def create_refresh_token(user_id: int) -> tuple[str, int]:
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = _create_token(str(user_id), int(expires_delta.total_seconds()), "refresh")
    return token, int(expires_delta.total_seconds())

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.JWT_ALGORITHM])
