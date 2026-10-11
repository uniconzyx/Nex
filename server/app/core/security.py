from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, secret: str, ttl_s: int, token_type: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_s),
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int) -> str:
    return _create_token(str(user_id), settings.jwt_secret, settings.access_token_ttl_s, "access")


def create_refresh_token(user_id: int) -> str:
    return _create_token(str(user_id), settings.jwt_refresh_secret, settings.refresh_token_ttl_s, "refresh")


def decode_token(token: str, expected_type: str) -> dict:
    secret = settings.jwt_secret if expected_type == "access" else settings.jwt_refresh_secret
    payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload
