# Двухсервисная система LLM-консультаций

Распределённая система из двух логически и технически независимых сервисов,
построенная по принципу разделения ответственности:

- **Auth Service** (FastAPI) — управление пользователями и выпуск JWT-токенов.
- **Bot Service** (aiogram + Celery) — Telegram-бот, который доверяет только
  корректно подписанному и не истёкшему JWT и общается с LLM через очередь.

Bot Service ничего не знает о пользователях, паролях и регистрации: он лишь
проверяет подпись и срок жизни токена, выданного Auth Service.


## Состав системы

Auth Service  - Регистрация, логин, выпуск и проверка JWT. Единственное место выпуска токенов. 
Bot Service   - Приём сообщений Telegram, валидация JWT, публикация задач в очередь. 
RabbitMQ      - Брокер задач Celery.                                            
Redis         - Result backend Celery **и** хранилище JWT, привязанного к Telegram `user_id`. 
Celery worker - Обработка задач: вызов OpenRouter и доставка ответа пользователю. 

JWT создаётся только в Auth Service. Bot Service токены не создаёт и не модифицирует.

## Структура репозитория

```
llm-consult-system/
├── docker-compose.yml
├── README.md
├── auth_service/
│   ├── pyproject.toml · pytest.ini · .env · Dockerfile
│   ├── app/
│   │   ├── main.py                  # сборка FastAPI, /health, lifespan
│   │   ├── core/  config.py · security.py · exceptions.py
│   │   ├── db/    base.py · session.py · models.py
│   │   ├── schemas/ auth.py · user.py
│   │   ├── repositories/ users.py   # только операции уровня БД
│   │   ├── usecases/ auth.py        # бизнес-логика (без SQL)
│   │   └── api/  deps.py · routes_auth.py · router.py
│   └── tests/ test_security.py (unit) · test_auth_api.py (integration)
└── bot_service/
    ├── pyproject.toml · pytest.ini · .env · Dockerfile
    ├── app/
    │   ├── main.py                  # FastAPI /health
    │   ├── core/  config.py · jwt.py (только проверка токена)
    │   ├── infra/ redis.py · celery_app.py
    │   ├── tasks/ llm_tasks.py      # Celery-задача llm_request
    │   ├── services/ openrouter_client.py
    │   └── bot/  dispatcher.py · handlers.py · runner.py
    └── tests/ test_jwt.py (unit) · test_handlers.py (mock) · test_openrouter.py (respx)
```

## Auth Service

Веб-API и Swagger: `http://0.0.0.0:8000/docs`.

| Метод | Endpoint         | Описание                                   |
|-------|------------------|--------------------------------------------|
| POST  | `/auth/register` | Создаёт пользователя (пароль хранится хешем)|
| POST  | `/auth/login`    | Возвращает JWT (form-data, OAuth2PasswordRequestForm) |
| GET   | `/auth/me`       | Профиль пользователя по валидному JWT       |
| GET   | `/health`        | Системная ручка                             |

JWT содержит поля `sub` (id пользователя), `role`, `iat`, `exp`.

## Bot Service

Действия пользователя:

1. Зарегистрироваться и получить токен в Auth Service (через Swagger).
2. Отправить токен боту: `/token <JWT>` — бот сохраняет его в Redis под ключом
   `token:<telegram_user_id>`.
3. Отправить обычное сообщение — бот валидирует JWT, публикует задачу в RabbitMQ
   и отвечает «Запрос принят. Ответ придёт следующим сообщением.».
4. Celery worker вызывает OpenRouter и присылает ответ следующим сообщением.

Без токена или с невалидным/истёкшим токеном бот отказывает в доступе и просит
пройти авторизацию в Auth Service. LLM-запрос никогда не выполняется прямо в
хэндлере — только через очередь.

## Запуск через Docker Compose

Заполните секреты в `.env`-файлах (одинаковый `JWT_SECRET` в обоих сервисах):

- `bot_service/.env`: `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`.
- При необходимости — модель `OPENROUTER_MODEL`.

```bash
docker compose up --build
```

Адреса после запуска:

- Auth Service Swagger — `http://localhost:8000/docs`
- RabbitMQ Management — `http://localhost:15672` (guest / guest)
- Bot Service `/health` — `http://localhost:8001/health`

Поднимаются сервисы: `auth_service`, `bot` (polling), `worker` (Celery),
`rabbitmq`, `redis`, `bot_api`.

## Локальный запуск без Docker (uv)

```bash
# Auth Service
cd auth_service
uv venv && source .venv/bin/activate
uv pip install -r <(uv pip compile pyproject.toml)
uvicorn app.main:app --reload --port 8000

# Bot Service (нужны запущенные redis и rabbitmq)
cd bot_service
uv venv && source .venv/bin/activate
uv pip install -r <(uv pip compile pyproject.toml)
python -m app.bot.runner                                   # бот
celery -A app.infra.celery_app:celery_app worker --loglevel=info  # воркер
```

## Тесты

Тесты не требуют Docker, реального Redis/RabbitMQ или доступа в интернет:
используются in-memory SQLite, `fakeredis`, `pytest-mock` и `respx`.

```bash
cd auth_service && uv run pytest -v
cd bot_service && uv run pytest -v
```

**Auth Service**
- `test_security.py` — unit: хеширование/проверка пароля, генерация и декодирование JWT.
- `test_auth_api.py` — integration через `httpx.ASGITransport`

**Bot Service**
- `test_jwt.py` — unit: валидный токен декодируется, мусор вызывает ошибку.
- `test_handlers.py` — mock: `/token` сохраняет токен в Redis; без токена Celery
  не вызывается; с токеном вызывается `llm_request.delay(...)` с верными аргументами.
- `test_openrouter.py` — integration через `respx`: корректное формирование
  payload и извлечение текста ответа.

## Демонстрация работы

Скриншоты в `docs/screenshots/`:

- `telegram_example.png` — сценарий в Telegram: `/token` → подтверждение →
  обычный вопрос → «Запрос принят» → ответ от LLM. Подтверждает, что доступ
  защищён JWT и запрос к LLM идёт не напрямую.
- `rabbitmq_overview.png` — интерфейс RabbitMQ: активные очереди, подключения и
  consumers (Connections: 4, Queues: 3, Consumers: 3). Подтверждает, что задачи
  реально проходят через брокер и обрабатываются асинхронно.
