from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_pass: str

    redis_host: str
    redis_port: int
    redis_password: str = ""

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int = 7

    bot_token: str

    password_policy_strict: bool = False

    rate_limit_auth_attempts: int = 5
    rate_limit_auth_seconds: int = 60

    origins: list
    log_level: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        auth = f":{quote(self.redis_password, safe='')}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"


settings = Settings()
