from jose import JWTError, jwt

from app.core.config import settings


def decode_and_validate(token: str) -> dict:
    """Проверяет подпись и срок жизни JWT, возвращает payload.

    Bot Service токены НЕ создаёт — только валидирует.
    Бросает ValueError, если токен неверный/истёк/без sub.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_alg]
        )
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc

    if not payload.get("sub"):
        raise ValueError("Token has no 'sub' claim")
    return payload
