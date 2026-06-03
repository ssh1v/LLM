import time

import pytest
from jose import jwt

from app.core.config import settings

try:  # совместимость разных версий fakeredis
    from fakeredis import FakeAsyncRedis
except ImportError:  # pragma: no cover
    from fakeredis.aioredis import FakeRedis as FakeAsyncRedis


def make_token(sub: str = "1", role: str = "user", exp_offset: int = 3600) -> str:
    now = int(time.time())
    payload = {"sub": sub, "role": role, "iat": now, "exp": now + exp_offset}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


@pytest.fixture
def fake_redis():
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def patch_redis(mocker, fake_redis):
    """Патчим get_redis именно там, где он используется (app.bot.handlers)."""
    mocker.patch("app.bot.handlers.get_redis", return_value=fake_redis)
    return fake_redis


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeChat:
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id


class FakeMessage:
    """Минимальная замена aiogram.types.Message для тестов хэндлеров."""

    def __init__(self, text: str, user_id: int = 1, chat_id: int = 1) -> None:
        self.text = text
        self.from_user = FakeUser(user_id)
        self.chat = FakeChat(chat_id)
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.answers.append(text)
