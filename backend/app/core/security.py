import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


# Custom Security Exceptions
class InvalidTokenException(Exception):
    """Raised when a token is invalid or malformed."""

    pass


class ExpiredTokenException(Exception):
    """Raised when a token has expired."""

    pass


class InvalidCredentialsException(Exception):
    """Raised when authentication credentials are invalid."""

    pass


# Password Hashing Utilities
def hash_password(password: str) -> str:
    """Hash a password using Argon2.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password string.
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        password: The plain text password to verify.
        hashed_password: The hashed password to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(password, hashed_password)


# JWT Token Utilities
def _create_token(
    subject: str | Any,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT token with specified type.

    Private helper function to avoid code duplication.

    Args:
        subject: The subject of the token (typically user ID).
        token_type: The type of token ("access" or "refresh").
        expires_delta: Optional custom expiration time.

    Returns:
        The encoded JWT token string.
    """
    now = datetime.now(UTC)

    if expires_delta:
        expire = now + expires_delta
    elif token_type == "access":
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:  # refresh
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": token_type,
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject of the token (typically user ID).
        expires_delta: Optional custom expiration time. If not provided,
                      uses ACCESS_TOKEN_EXPIRE_MINUTES from config.

    Returns:
        The encoded JWT access token string.
    """
    return _create_token(subject, "access", expires_delta)


def create_refresh_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token.

    Args:
        subject: The subject of the token (typically user ID).
        expires_delta: Optional custom expiration time. If not provided,
                      uses REFRESH_TOKEN_EXPIRE_DAYS from config.

    Returns:
        The encoded JWT refresh token string.
    """
    return _create_token(subject, "refresh", expires_delta)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and verify a JWT token.

    Args:
        token: The JWT token string to decode.
        expected_type: Optional expected token type ("access" or "refresh").
                      If provided, validates that the token type matches.

    Returns:
        The decoded token payload as a dictionary.

    Raises:
        InvalidTokenException: If the token is invalid, malformed, or missing required claims.
        ExpiredTokenException: If the token has expired.
    """
    logging.getLogger(__name__)
    pass
    pass

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        pass
    except ExpiredSignatureError:
        pass
        raise ExpiredTokenException("Token has expired")
    except JWTError as e:
        pass
        raise InvalidTokenException(f"Invalid token: {str(e)}")

    # Validate required claims
    required_claims = ["sub", "type", "iat", "exp"]
    missing_claims = [claim for claim in required_claims if claim not in payload]
    if missing_claims:
        pass
        raise InvalidTokenException(f"Token missing required claims: {', '.join(missing_claims)}")

    # Validate token type if expected
    if expected_type is not None:
        token_type = payload.get("type")
        if token_type != expected_type:
            pass
            raise InvalidTokenException(
                f"Expected token type '{expected_type}', got '{token_type}'"
            )

    pass
    return payload


# Security Constants
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


# Additional Utilities (preserved from original)
def generate_secret_key() -> str:
    """Generate a cryptographically secure random secret key.

    Returns:
        A hex-encoded random secret key.
    """
    return secrets.token_hex(32)


def hash_string(value: str) -> str:
    """Hash a string using SHA-256.

    Args:
        value: The string to hash.

    Returns:
        The hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(value.encode()).hexdigest()
