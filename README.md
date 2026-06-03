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

```bash
cd auth_service && uv run pytest -v
<img width="1280" height="344" alt="telegram-cloud-photo-size-2-5260489216049748557-y" src="https://github.com/user-attachments/assets/11454bdf-6946-4ecc-b663-8be7c7c31add" />

cd bot_service && uv run pytest -v
<img width="1280" height="319" alt="telegram-cloud-photo-size-2-5260489216049748559-y" src="https://github.com/user-attachments/assets/2df9eee8-1492-4e90-9e98-fcbf203bb85e" />

```

**Auth Service**
- `test_security.py` — unit: хеширование/проверка пароля, генерация и декодирование JWT.
- `test_auth_api.py` — integration через `httpx.ASGITransport`
<img width="1280" height="542" alt="telegram-cloud-photo-size-2-5260489216049748607-y" src="https://github.com/user-attachments/assets/124cd196-ff3c-4cff-920f-cda298fb85e6" />
<img width="1280" height="480" alt="telegram-cloud-photo-size-2-5260489216049748608-y" src="https://github.com/user-attachments/assets/e1d537f5-dba7-43c6-aaf0-b35596f71ce9" />
<img width="1280" height="530" alt="telegram-cloud-photo-size-2-5260489216049748609-y" src="https://github.com/user-attachments/assets/5f8d1804-d5b6-4079-bffb-a8b4a49a94c5" />


**Bot Service**
- `test_jwt.py` — unit: валидный токен декодируется, мусор вызывает ошибку.
- `test_handlers.py` — mock: `/token` сохраняет токен в Redis; без токена Celery
  не вызывается; с токеном вызывается `llm_request.delay(...)` с верными аргументами.
- `test_openrouter.py` — integration через `respx`: корректное формирование
  payload и извлечение текста ответа.

## Демонстрация работы

- `telegram_example.png`
<img width="1280" height="909" alt="telegram-cloud-photo-size-2-5260489216049748611-y" src="https://github.com/user-attachments/assets/97b0abd8-3315-4e89-9714-9a685859ec85" />

- `rabbitmq_overview.png` — интерфейс RabbitMQ: 
  <img width="1488" height="733" alt="image" src="https://github.com/user-attachments/assets/107b79d5-ccbd-4d22-9621-b50297ccf069" />

