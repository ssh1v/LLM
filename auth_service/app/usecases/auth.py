from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.users import UsersRepository


class AuthUseCase:
    """Бизнес-логика Auth Service. Никаких SQL-запросов напрямую — только репозиторий."""

    def __init__(self, repo: UsersRepository) -> None:
        self.repo = repo

    async def register(self, email: str, password: str) -> User:
        if await self.repo.get_by_email(email) is not None:
            raise UserAlreadyExistsError()
        return await self.repo.create(
            email=email, password_hash=hash_password(password)
        )

    async def login(self, email: str, password: str) -> str:
        user = await self.repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return create_access_token(sub=user.id, role=user.role)

    async def me(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user
