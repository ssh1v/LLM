from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.core.jwt import decode_and_validate
from app.infra.redis import get_redis
from app.tasks.llm_tasks import llm_request

router = Router()

START_TEXT = (
    "Это бот с доступом к большой языковой модели по JWT-токену.\n"
    "Сначала отправьте токен командой: /token <JWT>\n"
    "Потом просто напишите вопрос и я с удовольствием вам отвечу!"
)


def _token_key(tg_user_id: int) -> str:
    return f"token:{tg_user_id}"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("token"))
async def cmd_token(message: Message) -> None:
    """Сохраняет JWT в Redis под ключом token:<tg_user_id>."""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Использование: /token <JWT>")
        return

    token = parts[1].strip()
    redis = get_redis()
    await redis.set(_token_key(message.from_user.id), token)
    await message.answer("Токен сохранён. Теперь можно отправлять запросы модели.")


@router.message(F.text)
async def handle_text(message: Message) -> None:
    """Проверяет токен и публикует задачу к LLM в очередь (Celery -> RabbitMQ)."""
    redis = get_redis()
    token = await redis.get(_token_key(message.from_user.id))

    if not token:
        await message.answer(
            "Токен не найден. Сначала авторизуйтесь в Auth Service и отправьте "
            "токен командой: /token <JWT>"
        )
        return

    try:
        decode_and_validate(token)
    except ValueError:
        await message.answer(
            "Токен недействителен или истёк. Получите новый токен в Auth Service "
            "и отправьте его командой: /token <JWT>"
        )
        return

    # LLM-запрос НЕ выполняется в хэндлере — публикуем задачу в очередь.
    llm_request.delay(message.chat.id, message.text)
    await message.answer("Запрос принят. Ответ придёт следующим сообщением.")
