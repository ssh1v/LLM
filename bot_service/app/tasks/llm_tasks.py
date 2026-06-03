import logging

import httpx

from app.core.config import settings
from app.infra.celery_app import celery_app
from app.services.openrouter_client import call_openrouter

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LEN = 4000


def send_telegram_message(chat_id: int, text: str) -> None:
    """Отправляет сообщение пользователю через Telegram Bot API (синхронно)."""
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            json={"chat_id": chat_id, "text": text[:TELEGRAM_MAX_LEN]},
        )
        resp.raise_for_status()


@celery_app.task(name="llm_request")
def llm_request(tg_chat_id: int, prompt: str) -> str:
    """Фоновая задача: вызывает LLM и отправляет ответ пользователю.

    Возвращаемое значение сохраняется в Redis (result backend Celery).
    """
    try:
        answer = call_openrouter(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM request failed")
        answer = f"Произошла ошибка при обращении к LLM: {exc}"

    try:
        send_telegram_message(tg_chat_id, answer)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to deliver message to Telegram")

    return answer
