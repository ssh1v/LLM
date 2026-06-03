from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.repositories.users import UsersRepository
from app.usecases.auth import AuthUseCase

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_users_repo(session: AsyncSession = Depends(get_db)) -> UsersRepository:
    return UsersRepository(session)


def get_auth_uc(repo: UsersRepository = Depends(get_users_repo)) -> AuthUseCase:
    return AuthUseCase(repo)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """Достаёт и валидирует JWT из заголовка Authorization: Bearer ..."""
    try:
        payload = decode_token(token)
    except ValueError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError() from exc
        raise InvalidTokenError() from exc

    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError()
    return int(sub)
