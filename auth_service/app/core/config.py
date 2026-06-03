from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Единый объект настроек Auth Service.

    Значения читаются из переменных окружения / .env. Здесь нет кода,
    запускающего приложение или обращающегося к БД — только конфигурация.
    """

    app_name: str = "auth-service"
    env: str = "local"

    # JWT
    jwt_secret: str = "change_me_super_secret"
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 60

    # DB
    sqlite_path: str = "./auth.db"
    database_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_url(self) -> str:
        """Строка подключения для SQLAlchemy (async)."""
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.sqlite_path}"


settings = Settings()
