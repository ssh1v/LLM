import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Статусы, при которых имеет смысл повторить запрос (перегрузка/лимит провайдера).
RETRYABLE_STATUS = {429, 502, 503, 529}
MAX_RETRIES = 4
MAX_SLEEP_SECONDS = 20.0


def call_openrouter(prompt: str) -> str:
    """Синхронный клиент OpenRouter с авто-повтором при временных ошибках.

    Формирует payload /chat/completions, повторяет запрос при 429/5xx
    (уважая заголовок Retry-After) и возвращает текст ответа модели.
    Если все попытки исчерпаны или ошибка неустранимая — бросает RuntimeError.
    """
    url = f"{settings.openrouter_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
    }

    last_detail = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"OpenRouter network error: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]

        # Временная ошибка и попытки ещё остались — ждём и повторяем.
        if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else 2.0 * attempt
            except ValueError:
                delay = 2.0 * attempt
            delay = min(delay, MAX_SLEEP_SECONDS)
            last_detail = f"{response.status_code} (попытка {attempt}/{MAX_RETRIES})"
            logger.warning("OpenRouter %s — повтор через %.0f c", last_detail, delay)
            time.sleep(delay)
            continue

        # Неустранимая ошибка (например, 400/401/404) или попытки кончились.
        raise RuntimeError(
            f"OpenRouter returned {response.status_code}: {response.text}"
        )

    raise RuntimeError(f"OpenRouter не ответил после {MAX_RETRIES} попыток: {last_detail}")
