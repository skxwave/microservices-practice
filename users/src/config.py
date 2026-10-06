from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_url: str
    kafka_bootstrap_servers: str
    redis_url: str
    jwt_secret: str
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    debug: bool = False
    jwt_algorithm: str = "HS256"


settings = Settings()
