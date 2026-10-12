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

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    bot_token: str

    origins: list
    log_level: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
