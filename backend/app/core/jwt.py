"""JWT token generation and validation."""
import time
from typing import Optional
from jose import jwt, JWTError
import bcrypt
from ..core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def _secret_key() -> str:
    return settings.resolve_jwt_secret()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = time.time() + (expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        if payload.get("exp") and payload["exp"] < time.time():
            return None
        return payload
    except JWTError:
        return None
