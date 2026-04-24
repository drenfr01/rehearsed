"""Authentication utilities: JWT creation and verification with typed tokens."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth import Token

ALLOWED_EXTRA_CLAIMS = {"is_admin"}
VALID_TOKEN_TYPES = {"user", "session"}


def create_access_token(
    subject: str,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> Token:
    if token_type not in VALID_TOKEN_TYPES:
        raise ValueError(f"token_type must be one of {VALID_TOKEN_TYPES}")

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }

    if extra_claims:
        if not set(extra_claims.keys()).issubset(ALLOWED_EXTRA_CLAIMS):
            raise ValueError(f"extra_claims keys must be in {ALLOWED_EXTRA_CLAIMS}")
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return Token(access_token=encoded_jwt, expires_at=expire)


def _validate_token_format(token: str) -> None:
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")


def _decode_payload(token: str) -> Optional[dict]:
    _validate_token_format(token)
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        return None


def verify_token(token: str, expected_type: str) -> Optional[str]:
    payload = _decode_payload(token)
    if payload is None:
        return None
    if payload.get("type") != expected_type:
        logger.warning(
            "token_type_mismatch", expected=expected_type, got=payload.get("type")
        )
        return None
    subject = payload.get("sub")
    if subject is None:
        logger.warning("token_missing_subject")
    return subject


def verify_token_any_type(token: str) -> Optional[tuple[str, str]]:
    payload = _decode_payload(token)
    if payload is None:
        return None
    token_type = payload.get("type")
    subject = payload.get("sub")
    if not token_type or not subject:
        return None
    if token_type not in VALID_TOKEN_TYPES:
        logger.warning("token_unknown_type", token_type=token_type)
        return None
    return (subject, token_type)
