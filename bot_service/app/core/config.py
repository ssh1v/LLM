from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки Bot Service.

    Дефолты для брокеров заданы под docker-compose (rabbitmq/redis), а не localhost.
    """

    app_name: str = "bot-service"
    env: str = "local"

    # Telegram (.env: TELEGRAM_BOT_TOKEN)
    bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    auth_service_url: str = "http://auth_service:8000"

    # JWT — тот же секрет/алгоритм, что и в Auth Service (HS256)
    jwt_secret: str = "change_me_super_secret"
    jwt_alg: str = "HS256"

    # Инфраструктура
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672//"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openrouter_site_url: str = "https://example.com"
    openrouter_app_name: str = "bot-service"

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )


settings = Settings()
